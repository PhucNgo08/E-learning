from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.admin import quiz_service
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

router = APIRouter(
    prefix="/admin/quiz",
    tags=["Admin - Quiz Management"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "Quản lý Quiz",
        "active_page": "quiz",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/list", response_class=HTMLResponse)
def quiz_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    quizzes = quiz_service.get_all_quizzes_for_admin(db)
    return render_template(
        request,
        "quiz/list.html",
        {"quizzes": quizzes}
    )


@router.get("/delete/{quiz_id}", response_class=HTMLResponse)
def confirm_delete_quiz(
    quiz_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    quiz = quiz_service.get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz")

    return render_template(
        request,
        "quiz/delete.html",
        {"quiz": quiz, "page_title": "Xóa Quiz"}
    )


@router.post("/delete/{quiz_id}")
def delete_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    quiz = quiz_service.get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz")

    quiz_service.delete_quiz(db, quiz_id)
    return RedirectResponse(url="/admin/quiz/list", status_code=303)