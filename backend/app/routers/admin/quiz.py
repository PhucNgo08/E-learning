from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.quiz import Quiz
from app.services.admin import quiz_service

# ✅ Dùng template config chung
from app.config.template_config import get_template_by_path

# ============================================================
# 🚀 Router
# ============================================================
router = APIRouter(
    prefix="/admin/quiz",
    tags=["Admin - Quiz Management"]
)

# ============================================================
# 🧾 Danh sách quiz
# ============================================================
@router.get("/list", response_class=HTMLResponse)
def quiz_list(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    quizzes = quiz_service.get_all_quizzes(db)
    return tpl.TemplateResponse(
        "quiz/list.html",
        {"request": request, "quizzes": quizzes}
    )

# ============================================================
# ⚙️ Xóa quiz - Confirm
# ============================================================
@router.get("/delete/{quiz_id}", response_class=HTMLResponse)
def confirm_delete_quiz(quiz_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return tpl.TemplateResponse("quiz/delete.html", {"request": request, "quiz": quiz})

# ============================================================
# ⚙️ Thực hiện xóa quiz
# ============================================================
@router.post("/delete/{quiz_id}")
def delete_quiz(quiz_id: str, db: Session = Depends(get_db)):
    quiz_service.delete_quiz(db, quiz_id)
    return RedirectResponse(url="/admin/quiz/list", status_code=303)
