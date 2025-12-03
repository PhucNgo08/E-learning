"""
==========================================================
🎓 SERVICE: Student - Assignment (FINAL PRO MAX 2025)
Xử lý logic bài tập & bài nộp của Học Viên — FIX HOÀN HẢO
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.module import Module

from app.services.student.notification_service import create_notification

from datetime import datetime
from pathlib import Path
import uuid
import traceback
import shutil
import os


# ==========================================================
# 📁 Cấu hình thư mục upload bài nộp
# ==========================================================
UPLOAD_DIR = Path("uploads/assignments")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# 📘 LẤY DANH SÁCH BÀI TẬP TRONG KHÓA HỌC
# ==========================================================
def get_assignments_by_course(db: Session, course_id: str):
    try:
        assignments = (
            db.query(Assignment)
            .filter(Assignment.course_id == course_id)
            .order_by(Assignment.due_date.asc())
            .all()
        )

        if not assignments:
            return []

        for a in assignments:
            a.course = db.query(Course).filter(Course.id == a.course_id).first()
            a.module = (
                db.query(Module).filter(Module.id == a.module_id).first()
                if a.module_id else None
            )

        return assignments

    except Exception as e:
        print("❌ [get_assignments_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# ==========================================================
# 🔍 Lấy chi tiết 1 bài tập
# ==========================================================
def get_assignment_detail(db: Session, assignment_id: str):
    try:
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            return None

        assignment.course = db.query(Course).filter(Course.id == assignment.course_id).first()
        assignment.module = db.query(Module).filter(Module.id == assignment.module_id).first()

        return assignment

    except Exception as e:
        print("❌ [get_assignment_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📤 NỘP BÀI – VALIDATE FULL + RESUBMIT + NOTIFICATION
# ==========================================================
def submit_assignment(
    db: Session,
    assignment_id: str,
    student_id: str,
    submission_text: str = "",
    files: list = None
):
    try:
        now = datetime.now()

        # 1. Kiểm tra bài tập tồn tại
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            return {"status": "error", "message": "Không tìm thấy bài tập."}

        # 2. Kiểm tra học viên thuộc khóa học
        enrolled = db.query(Enrollment).filter_by(
            user_id=student_id,                      # 🔥 FIX QUAN TRỌNG
            course_id=assignment.course_id
        ).first()

        if not enrolled:
            return {"status": "error", "message": "Bạn không thuộc khóa học này."}

        # 3. Kiểm tra deadline
        if now > assignment.due_date:
            if assignment.allow_late_submission == 1:
                submission_status = "late"
            else:
                return {"status": "error", "message": "Đã quá hạn nộp và không cho phép nộp muộn."}
        else:
            submission_status = "submitted"

        # 4. Không được nộp bài trắng
        if not submission_text and (not files or len(files) == 0):
            return {"status": "error", "message": "Bạn phải nhập nội dung hoặc upload ít nhất 1 file."}

        # 5. Kiểm tra nộp lại
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == assignment_id)
            .filter(AssignmentSubmission.student_id == student_id)
            .first()
        )

        if submission:
            # Nộp lại
            submission.status = "resubmitted"
            submission.submission_time = now
            submission.submission_text = submission_text or submission.submission_text
        else:
            # Nộp mới
            submission = AssignmentSubmission(
                id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                student_id=student_id,
                submission_text=submission_text or "",
                submission_time=now,
                status=submission_status,
            )
            db.add(submission)

        db.commit()
        db.refresh(submission)

        # 6. Validate file
        if files:
            allowed_types = []
            if assignment.allowed_file_types:
                allowed_types = [
                    ext.strip().lower()
                    for ext in assignment.allowed_file_types.split(",")
                ]

            if assignment.max_files and len(files) > assignment.max_files:
                return {"status": "error", "message": f"Tối đa {assignment.max_files} file."}

            for f in files:
                if "." not in f.filename:
                    return {"status": "error", "message": f"File '{f.filename}' không hợp lệ."}

                ext = f.filename.split(".")[-1].lower()

                if allowed_types and ext not in allowed_types:
                    return {"status": "error", "message": f"File '{ext}' không được phép."}

                # Kiểm tra dung lượng
                f.file.seek(0, 2)
                size_mb = f.file.tell() / (1024 * 1024)
                f.file.seek(0)

                if size_mb > assignment.max_file_size_mb:
                    return {
                        "status": "error",
                        "message": f"File '{f.filename}' vượt quá {assignment.max_file_size_mb}MB."
                    }

        # 7. Lưu file
        if files:
            student_folder = UPLOAD_DIR / student_id
            student_folder.mkdir(parents=True, exist_ok=True)

            for f in files:
                safe_name = f"{uuid.uuid4().hex}_{f.filename}"
                file_path = student_folder / safe_name

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(f.file, buffer)

                file_record = AssignmentFile(
                    id=str(uuid.uuid4()),
                    submission_id=submission.id,
                    file_name=f.filename,
                    file_url=str(file_path),
                    file_type=f.content_type,
                    file_size=os.path.getsize(file_path),
                    uploaded_at=now
                )
                db.add(file_record)

            db.commit()

        # 8. Gửi thông báo cho giáo viên
        create_notification(
            db=db,
            user_id=assignment.teacher_id,
            title="📥 Có bài nộp mới",
            message=f"Sinh viên đã nộp bài tập: {assignment.title}",
            notification_type="assignment",
            link_url=f"/teacher/assignments/grade/{submission.id}"
        )

        return {"status": "ok", "submission": submission}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ==========================================================
# 📋 Lấy toàn bộ bài nộp của 1 học viên
# ==========================================================
def get_my_submissions(db: Session, student_id: str):
    try:
        subs = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.student_id == student_id)
            .order_by(AssignmentSubmission.submission_time.desc())
            .all()
        )

        if not subs:
            return []

        for s in subs:
            s.assignment = db.query(Assignment).filter(Assignment.id == s.assignment_id).first()
            if s.assignment:
                s.assignment.course = db.query(Course).filter(Course.id == s.assignment.course_id).first()

        return subs

    except:
        traceback.print_exc()
        return []


# ==========================================================
# 🔎 Xem chi tiết bài nộp
# ==========================================================
def get_submission_detail(db: Session, submission_id: str):
    try:
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )
        if not submission:
            return None

        submission.assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()

        submission.files = (
            db.query(AssignmentFile)
            .filter(AssignmentFile.submission_id == submission_id)
            .all()
        )

        return submission

    except:
        traceback.print_exc()
        return None


# ==========================================================
# 📎 Lấy file đính kèm
# ==========================================================
def get_submission_file(db: Session, file_id: str):
    try:
        return (
            db.query(AssignmentFile)
            .filter(AssignmentFile.id == file_id)
            .first()
        )
    except:
        traceback.print_exc()
        return None


# ==========================================================
# 📝 Cập nhật bài nộp (resubmit)
# ==========================================================
def update_submission(db: Session, submission_id: str, new_text: str = "", new_files: list = None):
    try:
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )
        if not submission:
            return None

        submission.submission_text = new_text.strip()
        submission.submission_time = datetime.now()
        submission.status = "resubmitted"

        db.commit()
        db.refresh(submission)

        # Lưu file mới
        if new_files:
            student_folder = UPLOAD_DIR / submission.student_id
            student_folder.mkdir(parents=True, exist_ok=True)

            for f in new_files:
                safe = f"{uuid.uuid4().hex}_{f.filename}"
                file_path = student_folder / safe

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(f.file, buffer)

                rec = AssignmentFile(
                    id=str(uuid.uuid4()),
                    submission_id=submission.id,
                    file_name=f.filename,
                    file_url=str(file_path),
                    file_type=f.content_type,
                    file_size=os.path.getsize(file_path),
                    uploaded_at=datetime.now()
                )
                db.add(rec)

            db.commit()

        return submission

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


# ==========================================================
# 🗑 XÓA BÀI NỘP
# ==========================================================
def delete_submission(db: Session, submission_id: str):
    try:
        submission = db.query(AssignmentSubmission).filter_by(id=submission_id).first()
        if not submission:
            return False

        files = (
            db.query(AssignmentFile)
            .filter(AssignmentFile.submission_id == submission_id)
            .all()
        )

        for f in files:
            try:
                if os.path.exists(f.file_url):
                    os.remove(f.file_url)
            except:
                pass
            db.delete(f)

        db.delete(submission)
        db.commit()

        # Dọn thư mục rỗng
        student_folder = UPLOAD_DIR / submission.student_id
        if os.path.isdir(student_folder) and not os.listdir(student_folder):
            os.rmdir(student_folder)

        return True

    except:
        db.rollback()
        traceback.print_exc()
        return False
