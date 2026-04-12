from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import shutil
import traceback
import uuid

from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.assignment_file import AssignmentFile
from app.models.assignment_group import AssignmentGroup
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.module import Module
from app.services.student.notification_service import create_notification


BACKEND_DIR = Path(__file__).resolve().parents[3]
UPLOAD_DIR = BACKEND_DIR / "uploads" / "assignments"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")


def _now() -> datetime:
    return datetime.utcnow()


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_files(files: list | None) -> list:
    normalized = []
    for f in files or []:
        if not f:
            continue
        filename = getattr(f, "filename", None)
        if not filename:
            continue
        if not str(filename).strip():
            continue
        normalized.append(f)
    return normalized


def _safe_filename(filename: str) -> str:
    return Path(filename).name.replace("..", "_")


def _get_allowed_extensions(assignment: Assignment) -> list[str]:
    raw = (assignment.allowed_file_types or "").strip()
    if not raw:
        return []
    return [part.strip().lower().lstrip(".") for part in raw.split(",") if part.strip()]


def _student_storage_folder(student_id: str) -> Path:
    folder = UPLOAD_DIR / str(student_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _is_remote_path(file_url: str | None) -> bool:
    if not file_url:
        return False
    lower = file_url.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def is_student_enrolled_in_course(db: Session, student_id: str, course_id: str) -> bool:
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.user_id == student_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .first()
        is not None
    )


def _get_student_group_for_assignment(db: Session, assignment_id: str, student_id: str) -> AssignmentGroup | None:
    """
    Hỗ trợ 2 trường hợp:
    1) Project đã có bảng assignment_group_members trong DB nhưng chưa có model
    2) Chưa có bảng thành viên nhóm -> fallback leader_id
    """
    try:
        row = db.execute(
            text(
                """
                SELECT ag.id
                FROM assignment_groups ag
                JOIN assignment_group_members agm ON agm.group_id = ag.id
                WHERE ag.assignment_id = :assignment_id
                  AND agm.user_id = :student_id
                LIMIT 1
                """
            ),
            {"assignment_id": assignment_id, "student_id": student_id},
        ).first()
        if row and row[0]:
            return db.query(AssignmentGroup).filter(AssignmentGroup.id == str(row[0])).first()
    except Exception:
        # DB/project chưa có bảng này hoặc chưa seed dữ liệu nhóm thành viên
        pass

    return (
        db.query(AssignmentGroup)
        .filter(
            AssignmentGroup.assignment_id == assignment_id,
            AssignmentGroup.leader_id == student_id,
        )
        .first()
    )


def _resolve_submission_target(
    db: Session,
    assignment: Assignment,
    student_id: str,
) -> dict:
    if assignment.submission_type == "group":
        group = _get_student_group_for_assignment(db, assignment.id, student_id)
        if not group:
            return {
                "ok": False,
                "message": "Bài tập này là bài tập nhóm nhưng bạn chưa thuộc nhóm nào.",
            }
        return {
            "ok": True,
            "mode": "group",
            "group": group,
            "student_id": None,
            "group_id": group.id,
        }

    return {
        "ok": True,
        "mode": "individual",
        "group": None,
        "student_id": student_id,
        "group_id": None,
    }


def _validate_submission_payload(
    assignment: Assignment,
    submission_text: str,
    files: list,
) -> str | None:
    cleaned_text = _clean_text(submission_text)
    normalized_files = _normalize_files(files)

    if not cleaned_text and not normalized_files:
        return "Bạn phải nhập nội dung hoặc tải lên ít nhất 1 file."

    if assignment.max_files and len(normalized_files) > int(assignment.max_files):
        return f"Tối đa {assignment.max_files} file."

    allowed_extensions = _get_allowed_extensions(assignment)

    for f in normalized_files:
        filename = str(getattr(f, "filename", "")).strip()
        if "." not in filename:
            return f"File '{filename}' không hợp lệ."

        ext = filename.rsplit(".", 1)[-1].lower()
        if allowed_extensions and ext not in allowed_extensions:
            return (
                f"File '{filename}' không đúng định dạng cho phép "
                f"({', '.join(allowed_extensions)})."
            )

        try:
            f.file.seek(0, 2)
            size_mb = f.file.tell() / (1024 * 1024)
            f.file.seek(0)
        except Exception:
            return f"Không đọc được file '{filename}'."

        if assignment.max_file_size_mb and size_mb > float(assignment.max_file_size_mb):
            return f"File '{filename}' vượt quá {assignment.max_file_size_mb}MB."

    return None


def _determine_submission_status(assignment: Assignment, now: datetime, is_resubmission: bool) -> str:
    is_late = bool(assignment.due_date and now > assignment.due_date)
    if is_late:
        return "late"
    if is_resubmission:
        return "resubmitted"
    return "submitted"


def _save_uploaded_files(
    db: Session,
    submission: AssignmentSubmission,
    student_id: str,
    files: list,
    uploaded_at: datetime,
) -> None:
    normalized_files = _normalize_files(files)
    if not normalized_files:
        return

    student_folder = _student_storage_folder(student_id)

    for f in normalized_files:
        original_name = _safe_filename(f.filename)
        safe_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = student_folder / safe_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        db.add(
            AssignmentFile(
                id=str(uuid.uuid4()),
                submission_id=submission.id,
                file_name=original_name,
                file_url=str(file_path),
                file_type=getattr(f, "content_type", None),
                file_size=os.path.getsize(file_path),
                uploaded_at=uploaded_at,
            )
        )


def _load_assignment_relations(db: Session, assignment: Assignment | None) -> Assignment | None:
    if not assignment:
        return None

    if not getattr(assignment, "course", None):
        assignment.course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if assignment.module_id and not getattr(assignment, "module", None):
        assignment.module = db.query(Module).filter(Module.id == assignment.module_id).first()
    return assignment


def _load_submission_relations(db: Session, submission: AssignmentSubmission | None) -> AssignmentSubmission | None:
    if not submission:
        return None

    submission.assignment = _load_assignment_relations(
        db,
        db.query(Assignment).filter(Assignment.id == submission.assignment_id).first(),
    )

    submission.files = (
        db.query(AssignmentFile)
        .filter(AssignmentFile.submission_id == submission.id)
        .order_by(AssignmentFile.uploaded_at.asc(), AssignmentFile.file_name.asc())
        .all()
    )

    if submission.group_id:
        submission.group = db.query(AssignmentGroup).filter(AssignmentGroup.id == submission.group_id).first()

    return submission


def get_assignments_by_course(db: Session, course_id: str):
    try:
        assignments = (
            db.query(Assignment)
            .options(joinedload(Assignment.course), joinedload(Assignment.module))
            .filter(Assignment.course_id == course_id)
            .order_by(Assignment.due_date.asc(), Assignment.created_at.desc())
            .all()
        )
        return assignments or []
    except Exception:
        traceback.print_exc()
        return []


def get_assignment_detail(db: Session, assignment_id: str):
    try:
        assignment = (
            db.query(Assignment)
            .options(joinedload(Assignment.course), joinedload(Assignment.module))
            .filter(Assignment.id == assignment_id)
            .first()
        )
        return assignment
    except Exception:
        traceback.print_exc()
        return None


def get_my_submission_for_assignment(db: Session, assignment_id: str, student_id: str):
    try:
        assignment = get_assignment_detail(db, assignment_id)
        if not assignment:
            return None

        target = _resolve_submission_target(db, assignment, student_id)
        if not target.get("ok"):
            return None

        query = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id
        )

        if target["mode"] == "group":
            query = query.filter(AssignmentSubmission.group_id == target["group_id"])
        else:
            query = query.filter(AssignmentSubmission.student_id == student_id)

        submission = query.first()
        return _load_submission_relations(db, submission)
    except Exception:
        traceback.print_exc()
        return None


def submit_assignment(
    db: Session,
    assignment_id: str,
    student_id: str,
    submission_text: str = "",
    files: list | None = None,
):
    try:
        files = _normalize_files(files)
        submission_text = _clean_text(submission_text)
        now = _now()

        assignment = get_assignment_detail(db, assignment_id)
        if not assignment:
            return {"status": "error", "message": "Không tìm thấy bài tập."}

        if not is_student_enrolled_in_course(db, student_id, assignment.course_id):
            return {"status": "error", "message": "Bạn không thuộc khóa học này."}

        if assignment.due_date and now > assignment.due_date and not bool(assignment.allow_late_submission):
            return {
                "status": "error",
                "message": "Đã quá hạn nộp và bài tập này không cho phép nộp muộn.",
            }

        validation_error = _validate_submission_payload(assignment, submission_text, files)
        if validation_error:
            return {"status": "error", "message": validation_error}

        target = _resolve_submission_target(db, assignment, student_id)
        if not target.get("ok"):
            return {"status": "error", "message": target.get("message", "Không thể xác định đối tượng nộp bài.")}

        query = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id
        )
        if target["mode"] == "group":
            query = query.filter(AssignmentSubmission.group_id == target["group_id"])
        else:
            query = query.filter(AssignmentSubmission.student_id == student_id)

        submission = query.first()
        is_resubmission = submission is not None
        new_status = _determine_submission_status(assignment, now, is_resubmission)

        if submission:
            submission.submission_text = submission_text or submission.submission_text
            submission.submission_time = now
            submission.status = new_status
        else:
            submission = AssignmentSubmission(
                id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                student_id=target["student_id"],
                group_id=target["group_id"],
                submission_text=submission_text,
                submission_time=now,
                status=new_status,
            )
            db.add(submission)

        db.flush()
        _save_uploaded_files(db, submission, student_id, files, now)
        db.commit()
        db.refresh(submission)

        try:
            create_notification(
                db=db,
                user_id=assignment.teacher_id,
                title="📥 Có bài nộp mới",
                message=f"Có bài nộp mới cho bài tập: {assignment.title}",
                notification_type="assignment",
                link_url=f"/teacher/assignments/grade/{submission.id}",
            )
        except Exception:
            # Không rollback vì nghiệp vụ nộp bài đã thành công
            traceback.print_exc()

        return {
            "status": "ok",
            "submission": _load_submission_relations(db, submission),
            "message": "Nộp bài thành công.",
        }
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def get_my_submissions(db: Session, student_id: str):
    try:
        group_ids: list[str] = []

        try:
            rows = db.execute(
                text(
                    """
                    SELECT ag.id
                    FROM assignment_groups ag
                    JOIN assignment_group_members agm ON agm.group_id = ag.id
                    WHERE agm.user_id = :student_id
                    """
                ),
                {"student_id": student_id},
            ).fetchall()
            group_ids.extend([str(r[0]) for r in rows if r and r[0]])
        except Exception:
            pass

        leader_groups = (
            db.query(AssignmentGroup.id)
            .filter(AssignmentGroup.leader_id == student_id)
            .all()
        )
        group_ids.extend([str(row[0]) for row in leader_groups if row and row[0]])
        group_ids = list(dict.fromkeys(group_ids))

        filters = [AssignmentSubmission.student_id == student_id]
        if group_ids:
            filters.append(AssignmentSubmission.group_id.in_(group_ids))

        submissions = (
            db.query(AssignmentSubmission)
            .options(joinedload(AssignmentSubmission.assignment))
            .filter(or_(*filters))
            .order_by(AssignmentSubmission.submission_time.desc())
            .all()
        )

        for submission in submissions:
            _load_submission_relations(db, submission)

        return submissions
    except Exception:
        traceback.print_exc()
        return []


def get_submission_detail(db: Session, submission_id: str):
    try:
        submission = (
            db.query(AssignmentSubmission)
            .options(joinedload(AssignmentSubmission.assignment))
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )
        return _load_submission_relations(db, submission)
    except Exception:
        traceback.print_exc()
        return None


def can_student_access_submission(db: Session, submission: AssignmentSubmission | None, student_id: str) -> bool:
    if not submission:
        return False

    if str(submission.student_id or "") == str(student_id):
        return True

    if submission.group_id:
        group = db.query(AssignmentGroup).filter(AssignmentGroup.id == submission.group_id).first()
        if group and str(group.leader_id or "") == str(student_id):
            return True

        try:
            row = db.execute(
                text(
                    """
                    SELECT 1
                    FROM assignment_group_members
                    WHERE group_id = :group_id AND user_id = :student_id
                    LIMIT 1
                    """
                ),
                {"group_id": submission.group_id, "student_id": student_id},
            ).first()
            if row:
                return True
        except Exception:
            pass

    return False


def get_submission_file(db: Session, file_id: str):
    try:
        return db.query(AssignmentFile).filter(AssignmentFile.id == file_id).first()
    except Exception:
        traceback.print_exc()
        return None


def resolve_file_response_target(file_info: AssignmentFile | None) -> dict:
    if not file_info:
        return {"ok": False, "message": "Không tìm thấy file."}

    file_url = str(file_info.file_url or "").strip()
    if not file_url:
        return {"ok": False, "message": "File không có đường dẫn hợp lệ."}

    if _is_remote_path(file_url):
        return {"ok": True, "type": "remote", "url": file_url}

    file_path = Path(file_url)
    if not file_path.is_absolute():
        file_path = (BACKEND_DIR / file_path).resolve()

    if not file_path.exists():
        return {"ok": False, "message": "File không tồn tại trên hệ thống."}

    return {"ok": True, "type": "local", "path": file_path}


def update_submission(
    db: Session,
    submission_id: str,
    student_id: str,
    new_text: str = "",
    new_files: list | None = None,
):
    try:
        submission = get_submission_detail(db, submission_id)
        if not submission:
            return {"status": "error", "message": "Không tìm thấy bài nộp."}

        if not can_student_access_submission(db, submission, student_id):
            return {"status": "error", "message": "Bạn không có quyền cập nhật bài nộp này."}

        assignment = submission.assignment
        new_files = _normalize_files(new_files)
        new_text = _clean_text(new_text)

        if assignment.due_date and _now() > assignment.due_date and not bool(assignment.allow_late_submission):
            return {"status": "error", "message": "Đã quá hạn và không được phép nộp lại."}

        validation_error = _validate_submission_payload(assignment, new_text or submission.submission_text, new_files)
        if validation_error:
            return {"status": "error", "message": validation_error}

        submission.submission_text = new_text or submission.submission_text
        submission.submission_time = _now()
        submission.status = _determine_submission_status(assignment, submission.submission_time, True)

        _save_uploaded_files(db, submission, student_id, new_files, submission.submission_time)
        db.commit()
        db.refresh(submission)

        return {
            "status": "ok",
            "submission": _load_submission_relations(db, submission),
            "message": "Cập nhật bài nộp thành công.",
        }
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def delete_submission(db: Session, submission_id: str, student_id: str):
    try:
        submission = get_submission_detail(db, submission_id)
        if not submission:
            return False

        if not can_student_access_submission(db, submission, student_id):
            return False

        files = db.query(AssignmentFile).filter(AssignmentFile.submission_id == submission_id).all()
        for f in files:
            try:
                target = resolve_file_response_target(f)
                if target.get("ok") and target.get("type") == "local":
                    os.remove(target["path"])
            except Exception:
                traceback.print_exc()
            db.delete(f)

        db.delete(submission)
        db.commit()

        folder = UPLOAD_DIR / str(student_id)
        if folder.exists() and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()

        return True
    except Exception:
        db.rollback()
        traceback.print_exc()
        return False
