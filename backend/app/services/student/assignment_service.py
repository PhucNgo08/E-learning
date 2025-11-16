"""
==========================================================
🎓 SERVICE: Student - Assignment (FULL 100%)
Xử lý logic bài tập & bài nộp của học viên
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
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
        return (
            db.query(Assignment)
            .filter(Assignment.course_id == course_id)
            .order_by(Assignment.due_date.asc())
            .all()
        )
    except Exception as e:
        print("❌ [get_assignments_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# ==========================================================
# 🔍 LẤY CHI TIẾT 1 BÀI TẬP
# ==========================================================
def get_assignment_detail(db: Session, assignment_id: str):
    try:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()
    except Exception as e:
        print("❌ [get_assignment_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📤 NỘP BÀI — FULL VALIDATE + THÔNG BÁO
# ==========================================================
def submit_assignment(
    db: Session,
    assignment_id: str,
    student_id: str,
    submission_text: str = "",
    files: list = None
):
    try:
        # ---------------------------
        # 1. Kiểm tra bài tập có tồn tại
        # ---------------------------
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            raise Exception("Không tìm thấy bài tập.")

        # ---------------------------
        # 2. Kiểm tra hạn nộp
        # ---------------------------
        now = datetime.utcnow()
        if now > assignment.due_date:
            if assignment.allow_late_submission == 1:
                submission_status = "late"
            else:
                raise Exception("Đã quá hạn nộp bài và không cho phép nộp muộn.")
        else:
            submission_status = "submitted"

        # ---------------------------
        # 3. Validate file upload
        # ---------------------------
        if files:
            # Kiểm tra số lượng file
            if assignment.max_files and len(files) > assignment.max_files:
                raise Exception(f"Chỉ được nộp tối đa {assignment.max_files} file.")

            # Allowed file types
            allowed_types = []
            if assignment.allowed_file_types:
                allowed_types = [
                    ext.strip().lower()
                    for ext in assignment.allowed_file_types.split(",")
                ]

            for f in files:
                # Kiểm tra loại file
                ext = f.filename.split(".")[-1].lower()
                if allowed_types and ext not in allowed_types:
                    raise Exception(f"Loại file '{ext}' không hợp lệ.")

                # Kiểm tra kích thước file
                f.file.seek(0, 2)
                size = f.file.tell()
                f.file.seek(0)

                size_mb = size / (1024 * 1024)
                if size_mb > assignment.max_file_size_mb:
                    raise Exception(
                        f"File '{f.filename}' vượt quá {assignment.max_file_size_mb}MB."
                    )

        # ---------------------------
        # 4. Tạo bài nộp
        # ---------------------------
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

        # ---------------------------
        # 5. Lưu FILE
        # ---------------------------
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
                    uploaded_at=datetime.utcnow()
                )
                db.add(file_record)

            db.commit()

        # ---------------------------
        # 6. Gửi thông báo cho GIẢNG VIÊN
        # ---------------------------
        create_notification(
            db=db,
            user_id=assignment.teacher_id,
            title="📥 Có bài tập mới được nộp",
            message=f"Sinh viên đã nộp bài: {assignment.title}",
            notification_type="assignment",
            link_url=f"/teacher/assignment/submission/{submission.id}"
        )

        print(f"✅ [submit_assignment] SV {student_id} đã nộp bài {assignment_id}")
        return submission

    except Exception as e:
        db.rollback()
        print("❌ [submit_assignment] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📋 LẤY DANH SÁCH BÀI NỘP CỦA SINH VIÊN
# ==========================================================
def get_my_submissions(db: Session, student_id: str):
    try:
        return (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.student_id == student_id)
            .order_by(AssignmentSubmission.submission_time.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_my_submissions] Lỗi:", e)
        traceback.print_exc()
        return []


# ==========================================================
# 🔎 LẤY CHI TIẾT MỘT BÀI NỘP
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

        submission.files = (
            db.query(AssignmentFile)
            .filter(AssignmentFile.submission_id == submission_id)
            .all()
        )
        return submission

    except Exception as e:
        print("❌ [get_submission_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📎 LẤY FILE ĐỂ TẢI XUỐNG
# ==========================================================
def get_submission_file(db: Session, file_id: str):
    try:
        return db.query(AssignmentFile).filter(AssignmentFile.id == file_id).first()
    except Exception as e:
        print("❌ [get_submission_file] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📝 CẬP NHẬT BÀI NỘP
# ==========================================================
def update_submission(db: Session, submission_id: str, new_text: str = "", new_files: list = None):
    try:
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )
        if not submission:
            print("⚠️ [update_submission] Không tìm thấy bài nộp.")
            return None

        # Cập nhật nội dung text
        if new_text:
            submission.submission_text = new_text.strip()
            submission.submission_time = datetime.utcnow()

        db.commit()
        db.refresh(submission)

        # Lưu file mới
        if new_files:
            student_folder = UPLOAD_DIR / submission.student_id
            student_folder.mkdir(parents=True, exist_ok=True)

            for f in new_files:
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
                    uploaded_at=datetime.utcnow()
                )
                db.add(file_record)

            db.commit()

        print(f"✅ [update_submission] Đã cập nhật bài nộp {submission_id}")
        return submission

    except Exception as e:
        db.rollback()
        print("❌ [update_submission] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 🗑️ XÓA BÀI NỘP
# ==========================================================
def delete_submission(db: Session, submission_id: str):
    try:
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )
        if not submission:
            print("⚠️ [delete_submission] Không tìm thấy bài nộp.")
            return False

        # Xóa file vật lý
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

        # Xóa bài nộp
        db.delete(submission)
        db.commit()

        print(f"🗑️ [delete_submission] Đã xóa bài nộp {submission_id}")
        return True

    except Exception as e:
        db.rollback()
        print("❌ [delete_submission] Lỗi:", e)
        traceback.print_exc()
        return False
