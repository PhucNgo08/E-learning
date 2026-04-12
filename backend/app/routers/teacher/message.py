"""
==========================================================
📨 ROUTER: Teacher - Message
Quản lý hệ thống tin nhắn nội bộ cho giáo viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_teacher
from app.services.teacher import message_service
from app.models.user import User

router = APIRouter(
    prefix="/teacher/message",
    tags=["Teacher - Message"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "active_page": "message",
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/message/inbox", status_code=303)


@router.get("/inbox", response_class=HTMLResponse)
async def inbox(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    messages = message_service.get_inbox_messages(db, teacher.id)

    return render_template(
        request,
        "message/inbox.html",
        {
            "teacher": teacher,
            "messages": messages,
            "page_title": "📥 Hộp thư đến",
        },
    )


@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    messages = message_service.get_sent_messages(db, teacher.id)

    return render_template(
        request,
        "message/sent.html",
        {
            "teacher": teacher,
            "messages": messages,
            "page_title": "📤 Thư đã gửi",
        },
    )


@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(
    request: Request,
    message_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    message = message_service.get_message_detail_for_user(db, message_id, teacher.id)

    if not message:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn.")

    return render_template(
        request,
        "message/view_message.html",
        {
            "teacher": teacher,
            "message": message,
            "page_title": "📨 Chi tiết tin nhắn",
        },
    )


@router.get("/compose", response_class=HTMLResponse)
async def compose_page(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher

    return render_template(
        request,
        "message/compose_message.html",
        {
            "teacher": teacher,
            "page_title": "✉️ Soạn tin nhắn mới",
        },
    )


@router.post("/compose")
async def send_message(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    receiver_id: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile | None = File(None),
):
    sender = current_teacher

    receiver = (
        db.query(User)
        .filter((User.email == receiver_id) | (User.id == receiver_id))
        .first()
    )
    if not receiver:
        raise HTTPException(status_code=400, detail="Không tìm thấy người nhận trong hệ thống.")

    result = message_service.send_message(
        db=db,
        sender_id=sender.id,
        receiver_id=receiver.id,
        content=content,
        attachment=attachment,
    )

    if not result or "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"] if result and "error" in result else "Không thể gửi tin nhắn."
        )

    return RedirectResponse(
        url="/teacher/message/sent",
        status_code=status.HTTP_303_SEE_OTHER
    )