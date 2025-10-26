from sqlalchemy.orm import Session
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from datetime import datetime
import uuid
import traceback

# ==========================================================
# 🎓 HỌC VIÊN – XỬ LÝ BÀI TẬP
# ==========================================================

def get_assignments_by_course(db: Session, course_id: str):
    """📘 Lấy danh sách bài tập trong khóa học"""
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


def get_assignment_detail(db: Session, assignment_id: str):
    """🔍 Lấy thông tin chi tiết 1 bài tập"""
    try:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()
    except Exception as e:
        print("❌ [get_assignment_detail] Lỗi:", e)
        traceback.print_exc()
        return None


def submit_assignment(db: Session, assignment_id: str, student_id: str, submission_text: str = "", files: list = None):
    """📤 Sinh viên nộp bài"""
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

        # Đính kèm file
        if files:
            for f in files:
                file_record = AssignmentFile(
                    id=str(uuid.uuid4()),
                    submission_id=submission.id,
                    file_name=f.filename,
                    file_url=f"/uploads/assignments/{f.filename}",
                    file_type=f.content_type,
                    file_size=0,
                    uploaded_at=datetime.utcnow()
                )
                db.add(file_record)
            db.commit()

        return submission
    except Exception as e:
        db.rollback()
        print("❌ [submit_assignment] Lỗi:", e)
        traceback.print_exc()
        return None


def get_my_submissions(db: Session, student_id: str):
    """📋 Lấy danh sách bài tập sinh viên đã nộp"""
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


def get_submission_detail(db: Session, submission_id: str):
    """🔎 Lấy chi tiết 1 bài nộp (kèm file)"""
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
