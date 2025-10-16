from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.quiz import Quiz
import uuid, datetime

exam_router = APIRouter(prefix="/admin/exams", tags=["Admin - Exam Management"])

# 📋 Lấy danh sách kỳ thi
@exam_router.get("/")
def get_exams(db: Session = Depends(get_db)):
    exams = db.query(Quiz).all()
    return exams

# ➕ Tạo kỳ thi mới
@exam_router.post("/")
def create_exam(
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(None),
    teacher_id: str = Form(None),
    total_questions: int = Form(10),
    db: Session = Depends(get_db),
):
    try:
        new_exam = Quiz(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            course_id=course_id,
            created_at=datetime.datetime.now(),
            total_questions=total_questions,
        )
        db.add(new_exam)
        db.commit()
        return {"message": "Tạo kỳ thi thành công!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo kỳ thi: {str(e)}")

# ✏️ Cập nhật kỳ thi
@exam_router.put("/{exam_id}")
def update_exam(exam_id: str, title: str = Form(...), description: str = Form(None), db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi.")
    exam.title = title
    exam.description = description
    db.commit()
    return {"message": "Cập nhật thành công"}

# ❌ Xóa kỳ thi
@exam_router.delete("/{exam_id}")
def delete_exam(exam_id: str, db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi.")
    db.delete(exam)
    db.commit()
    return {"message": "Đã xóa kỳ thi"}
