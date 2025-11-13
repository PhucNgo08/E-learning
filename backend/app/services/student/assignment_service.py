"""
=========================================================
🎓 SERVICE: Student - Assignment
Xử lý logic bài tập và bài nộp của học viên
=========================================================
"""

from sqlalchemy.orm import Session
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
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
    """📘 Lấy danh sách bài tập thuộc một khóa học"""
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
    """🔍 Lấy chi tiết một bài tập"""
    try:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()
    except Exception as e:
        print("❌ [get_assignment_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📤 SINH VIÊN NỘP BÀI (CÓ THỂ KÈM FILE)
# ==========================================================
def submit_assignment(db: Session, assignment_id: str, student_id: str, submission_text: str = "", files: list = None):
    """📤 Sinh viên nộp bài (lưu cả file vào thư mục uploads/assignments/)"""
    try:
        submission = AssignmentSubmission(
            id=str(uuid.uuid4()),
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=submission_text or "",
            submission_time=datetime.utcnow(),
            status="submitted"
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        # ✅ Lưu file nếu có
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

        print(f"✅ [submit_assignment] Sinh viên {student_id} đã nộp bài {assignment_id}")
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
    """📋 Lấy danh sách bài nộp của sinh viên"""
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
# 🔎 LẤY CHI TIẾT 1 BÀI NỘP (KÈM FILE)
# ==========================================================
def get_submission_detail(db: Session, submission_id: str):
    """🔎 Lấy chi tiết một bài nộp, bao gồm file đính kèm"""
    try:
        submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
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
# 📎 LẤY THÔNG TIN FILE NỘP BÀI (TẢI XUỐNG)
# ==========================================================
def get_submission_file(db: Session, file_id: str):
    """📎 Lấy thông tin chi tiết file nộp bài để tải xuống"""
    try:
        return db.query(AssignmentFile).filter(AssignmentFile.id == file_id).first()
    except Exception as e:
        print("❌ [get_submission_file] Lỗi:", e)
        traceback.print_exc()
        return None


# ==========================================================
# 📝 CẬP NHẬT BÀI NỘP (THÊM FILE HOẶC SỬA NỘI DUNG)
# ==========================================================
def update_submission(db: Session, submission_id: str, new_text: str = "", new_files: list = None):
    """📝 Cập nhật bài nộp (sửa nội dung hoặc thêm file mới)"""
    try:
        submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
        if not submission:
            print("⚠️ [update_submission] Không tìm thấy bài nộp.")
            return None

        # Cập nhật nội dung
        if new_text:
            submission.submission_text = new_text.strip()
            submission.submission_time = datetime.utcnow()

        db.commit()
        db.refresh(submission)

        # Thêm file mới nếu có
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
    """🗑️ Xóa bài nộp và tất cả file liên quan"""
    try:
        submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
        if not submission:
            print("⚠️ [delete_submission] Không tìm thấy bài nộp.")
            return False

        # Xóa file vật lý và bản ghi file
        files = db.query(AssignmentFile).filter(AssignmentFile.submission_id == submission_id).all()
        for f in files:
            try:
                if os.path.exists(f.file_url):
                    os.remove(f.file_url)
            except Exception as file_err:
                print(f"⚠️ [delete_submission] Không thể xóa file {f.file_url}: {file_err}")
            db.delete(f)

        # Xóa bài nộp
        db.delete(submission)
        db.commit()

        print(f"✅ [delete_submission] Đã xóa bài nộp {submission_id}")
        return True

    except Exception as e:
        db.rollback()
        print("❌ [delete_submission] Lỗi:", e)
        traceback.print_exc()
        return False
