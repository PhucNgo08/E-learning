from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.dependencies.auth import get_current_admin

router = APIRouter(
    prefix="/admin/exams",
    tags=["Quản trị - Chuyển hướng kỳ thi cũ"],
    dependencies=[Depends(get_current_admin)],
)


def _go(url: str = "/admin/quiz/list") -> RedirectResponse:
    """Chuyển các đường dẫn cũ /admin/exams về trang quản lý kỳ thi mới."""
    return RedirectResponse(url, status_code=303)


@router.get("")
@router.get("/")
@router.get("/manage")
def exams_manage_redirect():
    return _go("/admin/quiz/list")


@router.get("/create")
@router.post("/create")
@router.get("/{exam_id}/edit")
@router.post("/{exam_id}/edit")
@router.get("/{exam_id}/questions")
@router.get("/{exam_id}/questions/add")
@router.post("/{exam_id}/questions/add")
@router.get("/{exam_id}/questions/{question_id}/edit")
@router.post("/{exam_id}/questions/{question_id}/edit")
@router.get("/{exam_id}/questions/{question_id}/delete")
@router.post("/{exam_id}/questions/{question_id}/delete")
@router.get("/{exam_id}/import")
@router.post("/{exam_id}/import")
@router.post("/{exam_id}/import/confirm")
@router.post("/{exam_id}/approve")
@router.post("/{exam_id}/reject")
@router.get("/{exam_id}/delete")
@router.post("/{exam_id}/delete")
def exams_old_routes_redirect():
    # Trang /admin/quiz hiện là module chính. Các route create/edit/import của module exams cũ không dùng nữa.
    return _go("/admin/quiz/list")
