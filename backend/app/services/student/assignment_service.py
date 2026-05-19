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


# ======================================================
# 📁 Cấu hình lưu file bài nộp
# ======================================================
BACKEND_DIR = Path(__file__).resolve().parents[3]
UPLOAD_DIR = BACKEND_DIR / "uploads" / "assignments"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")


# ======================================================
# 🔧 Helper chung
# ======================================================
def _now() -> datetime:
    return datetime.utcnow()


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_files(files: list | None) -> list:
    normalized = []

    for file in files or []:
        if not file:
            continue

        filename = getattr(file, "filename", None)
        if not filename:
            continue

        if not str(filename).strip():
            continue

        normalized.append(file)

    return normalized


def _safe_filename(filename: str) -> str:
    safe = Path(filename or "").name
    safe = safe.replace("..", "_")
    safe = safe.replace("/", "_").replace("\\", "_")
    return safe.strip() or "uploaded_file"


def _get_file_extension(filename: str) -> str:
    """
    Lưu file_type dạng ngắn: pdf/docx/zip...
    Không lưu MIME type dài như:
    application/vnd.openxmlformats-officedocument.wordprocessingml.document
    vì cột assignment_files.file_type trong DB thường ngắn và sẽ lỗi Data too long.
    """
    filename = str(filename or "").strip()
    if "." not in filename:
        return "file"
    return filename.rsplit(".", 1)[-1].lower()[:30]


def _get_allowed_extensions(assignment: Assignment) -> list[str]:
    raw = (assignment.allowed_file_types or "").strip()
    if not raw:
        return []

    return [
        part.strip().lower().lstrip(".")
        for part in raw.split(",")
        if part.strip()
    ]


def _student_storage_folder(student_id: str) -> Path:
    folder = UPLOAD_DIR / str(student_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _is_remote_path(file_url: str | None) -> bool:
    if not file_url:
        return False

    lower = str(file_url).lower().strip()
    return lower.startswith("http://") or lower.startswith("https://")


def _file_size_mb(upload_file) -> float:
    upload_file.file.seek(0, 2)
    size = upload_file.file.tell()
    upload_file.file.seek(0)
    return size / (1024 * 1024)


# ======================================================
# ✅ Kiểm tra quyền học khóa
# ======================================================
def is_student_enrolled_in_course(db: Session, student_id: str, course_id: str) -> bool:
    if not student_id or not course_id:
        return False

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


# ======================================================
# 👥 Xử lý bài tập nhóm
# ======================================================
def _get_student_group_for_assignment(
    db: Session,
    assignment_id: str,
    student_id: str,
) -> AssignmentGroup | None:
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
            {
                "assignment_id": assignment_id,
                "student_id": student_id,
            },
        ).first()

        if row and row[0]:
            return (
                db.query(AssignmentGroup)
                .filter(AssignmentGroup.id == str(row[0]))
                .first()
            )

    except Exception:
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
    if (assignment.submission_type or "").lower() == "group":
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


# ======================================================
# ✅ Validate nội dung nộp bài
# ======================================================
def _validate_submission_payload(
    assignment: Assignment,
    submission_text: str,
    files: list,
) -> str | None:
    cleaned_text = _clean_text(submission_text)
    normalized_files = _normalize_files(files)

    if not cleaned_text and not normalized_files:
        return "Bạn phải nhập nội dung hoặc tải lên ít nhất 1 file."

    max_files = int(assignment.max_files or 0)
    if max_files > 0 and len(normalized_files) > max_files:
        return f"Tối đa {max_files} file."

    allowed_extensions = _get_allowed_extensions(assignment)

    for upload_file in normalized_files:
        filename = str(getattr(upload_file, "filename", "") or "").strip()

        if "." not in filename:
            return f"File '{filename}' không hợp lệ."

        ext = filename.rsplit(".", 1)[-1].lower()

        if allowed_extensions and ext not in allowed_extensions:
            return (
                f"File '{filename}' không đúng định dạng cho phép "
                f"({', '.join(allowed_extensions)})."
            )

        try:
            size_mb = _file_size_mb(upload_file)
        except Exception:
            return f"Không đọc được file '{filename}'."

        max_size = float(assignment.max_file_size_mb or 0)
        if max_size > 0 and size_mb > max_size:
            return f"File '{filename}' vượt quá {assignment.max_file_size_mb}MB."

    return None


def _determine_submission_status(
    assignment: Assignment,
    now: datetime,
    is_resubmission: bool,
) -> str:
    is_late = bool(assignment.due_date and now > assignment.due_date)

    if is_late:
        return "late"

    if is_resubmission:
        return "resubmitted"

    return "submitted"


# ======================================================
# 💾 Lưu file bài nộp
# ======================================================
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

    for upload_file in normalized_files:
        original_name = _safe_filename(upload_file.filename)
        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = student_folder / stored_name
        file_ext = _get_file_extension(original_name)

        upload_file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        db.add(
            AssignmentFile(
                id=str(uuid.uuid4()),
                submission_id=submission.id,
                file_name=original_name,
                file_url=str(file_path),
                file_type=file_ext,  # ✅ FIX: lưu docx/pdf/zip, không lưu MIME dài
                file_size=os.path.getsize(file_path),
                uploaded_at=uploaded_at,
            )
        )


# ======================================================
# 🔄 Load relation thủ công để template dùng ổn
# ======================================================
def _load_assignment_relations(
    db: Session,
    assignment: Assignment | None,
) -> Assignment | None:
    if not assignment:
        return None

    if not getattr(assignment, "course", None):
        assignment.course = (
            db.query(Course)
            .filter(Course.id == assignment.course_id)
            .first()
        )

    if assignment.module_id and not getattr(assignment, "module", None):
        assignment.module = (
            db.query(Module)
            .filter(Module.id == assignment.module_id)
            .first()
        )

    return assignment


def _load_submission_relations(
    db: Session,
    submission: AssignmentSubmission | None,
) -> AssignmentSubmission | None:
    if not submission:
        return None

    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == submission.assignment_id)
        .first()
    )
    submission.assignment = _load_assignment_relations(db, assignment)

    submission.files = (
        db.query(AssignmentFile)
        .filter(AssignmentFile.submission_id == submission.id)
        .order_by(
            AssignmentFile.uploaded_at.asc(),
            AssignmentFile.file_name.asc(),
        )
        .all()
    )

    if submission.group_id:
        submission.group = (
            db.query(AssignmentGroup)
            .filter(AssignmentGroup.id == submission.group_id)
            .first()
        )

    return submission


# ======================================================
# 📋 Danh sách / chi tiết bài tập
# ======================================================
def get_assignments_by_course(db: Session, course_id: str):
    try:
        return (
            db.query(Assignment)
            .options(
                joinedload(Assignment.course),
                joinedload(Assignment.module),
            )
            .filter(Assignment.course_id == course_id)
            .order_by(
                Assignment.due_date.asc(),
                Assignment.created_at.desc(),
            )
            .all()
            or []
        )
    except Exception:
        traceback.print_exc()
        return []


def get_assignment_detail(db: Session, assignment_id: str):
    try:
        return (
            db.query(Assignment)
            .options(
                joinedload(Assignment.course),
                joinedload(Assignment.module),
            )
            .filter(Assignment.id == assignment_id)
            .first()
        )
    except Exception:
        traceback.print_exc()
        return None


# ======================================================
# 📌 Bài nộp của sinh viên
# ======================================================
def get_my_submission_for_assignment(
    db: Session,
    assignment_id: str,
    student_id: str,
):
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

        submission = (
            query.order_by(AssignmentSubmission.submission_time.desc())
            .first()
        )

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
            return {
                "status": "error",
                "message": "Không tìm thấy bài tập.",
            }

        if not is_student_enrolled_in_course(db, student_id, assignment.course_id):
            return {
                "status": "error",
                "message": "Bạn không thuộc khóa học này.",
            }

        is_late = bool(assignment.due_date and now > assignment.due_date)
        if is_late and not bool(assignment.allow_late_submission):
            return {
                "status": "error",
                "message": "Đã quá hạn nộp và bài tập này không cho phép nộp muộn.",
            }

        validation_error = _validate_submission_payload(
            assignment,
            submission_text,
            files,
        )
        if validation_error:
            return {
                "status": "error",
                "message": validation_error,
            }

        target = _resolve_submission_target(db, assignment, student_id)
        if not target.get("ok"):
            return {
                "status": "error",
                "message": target.get(
                    "message",
                    "Không thể xác định đối tượng nộp bài.",
                ),
            }

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
            if submission_text:
                submission.submission_text = submission_text
            submission.submission_time = now
            submission.status = new_status
            submission.grade = None
            submission.feedback = None
            submission.graded_by = None
            submission.graded_at = None
            if hasattr(submission, "updated_at"):
                submission.updated_at = now
        else:
            submission_data = {
                "id": str(uuid.uuid4()),
                "assignment_id": assignment_id,
                "student_id": target["student_id"],
                "group_id": target["group_id"],
                "submission_text": submission_text,
                "submission_time": now,
                "status": new_status,
            }

            if hasattr(AssignmentSubmission, "created_at"):
                submission_data["created_at"] = now
            if hasattr(AssignmentSubmission, "updated_at"):
                submission_data["updated_at"] = now

            submission = AssignmentSubmission(**submission_data)
            db.add(submission)

        db.flush()

        _save_uploaded_files(
            db=db,
            submission=submission,
            student_id=student_id,
            files=files,
            uploaded_at=now,
        )

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
            traceback.print_exc()

        return {
            "status": "ok",
            "submission": _load_submission_relations(db, submission),
            "message": "Nộp bài thành công.",
        }

    except Exception as exc:
        db.rollback()
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(exc),
        }


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

            group_ids.extend([str(row[0]) for row in rows if row and row[0]])

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


# ======================================================
# 🔐 Quyền xem / tải file bài nộp
# ======================================================
def can_student_access_submission(
    db: Session,
    submission: AssignmentSubmission | None,
    student_id: str,
) -> bool:
    if not submission:
        return False

    if str(submission.student_id or "") == str(student_id):
        return True

    if submission.group_id:
        group = (
            db.query(AssignmentGroup)
            .filter(AssignmentGroup.id == submission.group_id)
            .first()
        )

        if group and str(group.leader_id or "") == str(student_id):
            return True

        try:
            row = db.execute(
                text(
                    """
                    SELECT 1
                    FROM assignment_group_members
                    WHERE group_id = :group_id
                      AND user_id = :student_id
                    LIMIT 1
                    """
                ),
                {
                    "group_id": submission.group_id,
                    "student_id": student_id,
                },
            ).first()

            if row:
                return True

        except Exception:
            pass

    return False


def get_submission_file(db: Session, file_id: str):
    try:
        return (
            db.query(AssignmentFile)
            .filter(AssignmentFile.id == file_id)
            .first()
        )
    except Exception:
        traceback.print_exc()
        return None


def resolve_file_response_target(file_info: AssignmentFile | None) -> dict:
    if not file_info:
        return {
            "ok": False,
            "message": "Không tìm thấy file.",
        }

    file_url = str(file_info.file_url or "").strip()
    if not file_url:
        return {
            "ok": False,
            "message": "File không có đường dẫn hợp lệ.",
        }

    if _is_remote_path(file_url):
        return {
            "ok": True,
            "type": "remote",
            "url": file_url,
        }

    file_path = Path(file_url)

    if not file_path.is_absolute():
        file_path = (BACKEND_DIR / file_path).resolve()

    if not file_path.exists():
        return {
            "ok": False,
            "message": "File không tồn tại trên hệ thống.",
        }

    return {
        "ok": True,
        "type": "local",
        "path": file_path,
    }


# ======================================================
# ✏️ Cập nhật / xóa bài nộp
# ======================================================
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
            return {
                "status": "error",
                "message": "Không tìm thấy bài nộp.",
            }

        if not can_student_access_submission(db, submission, student_id):
            return {
                "status": "error",
                "message": "Bạn không có quyền cập nhật bài nộp này.",
            }

        assignment = submission.assignment
        new_files = _normalize_files(new_files)
        new_text = _clean_text(new_text)

        if assignment.due_date and _now() > assignment.due_date and not bool(assignment.allow_late_submission):
            return {
                "status": "error",
                "message": "Đã quá hạn và không được phép nộp lại.",
            }

        validation_error = _validate_submission_payload(
            assignment,
            new_text or submission.submission_text,
            new_files,
        )
        if validation_error:
            return {
                "status": "error",
                "message": validation_error,
            }

        now = _now()
        if new_text:
            submission.submission_text = new_text
        submission.submission_time = now
        submission.status = _determine_submission_status(assignment, now, True)
        submission.grade = None
        submission.feedback = None
        submission.graded_by = None
        submission.graded_at = None
        if hasattr(submission, "updated_at"):
            submission.updated_at = now

        _save_uploaded_files(
            db=db,
            submission=submission,
            student_id=student_id,
            files=new_files,
            uploaded_at=now,
        )

        db.commit()
        db.refresh(submission)

        return {
            "status": "ok",
            "submission": _load_submission_relations(db, submission),
            "message": "Cập nhật bài nộp thành công.",
        }

    except Exception as exc:
        db.rollback()
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(exc),
        }


def delete_submission(db: Session, submission_id: str, student_id: str):
    try:
        submission = get_submission_detail(db, submission_id)
        if not submission:
            return False

        if not can_student_access_submission(db, submission, student_id):
            return False

        files = (
            db.query(AssignmentFile)
            .filter(AssignmentFile.submission_id == submission_id)
            .all()
        )

        for file_info in files:
            try:
                target = resolve_file_response_target(file_info)
                if target.get("ok") and target.get("type") == "local":
                    os.remove(target["path"])
            except Exception:
                traceback.print_exc()

            db.delete(file_info)

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
