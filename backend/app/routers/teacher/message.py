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

# ✅ Import cấu hình & service
from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_teacher
from app.services.teacher import message_service
from app.models.user import User


# ======================================================
# 🚀 Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/teacher/message",
    tags=["Teacher - Message"]
)


# ======================================================
# 🧭 0️⃣ Redirect gốc → /inbox
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Chuyển hướng /teacher/message → /teacher/message/inbox"""
    return RedirectResponse("/teacher/message/inbox", status_code=303)


# ======================================================
# 📥 1️⃣ Hộp thư đến (Inbox)
# ======================================================
@router.get("/inbox", response_class=HTMLResponse)
async def inbox(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị hộp thư đến của giáo viên"""
    teacher = current_teacher
    messages = message_service.get_inbox_messages(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "message/inbox.html",
        {
            "request": request,
            "teacher": teacher,
            "messages": messages,
            "page_title": "📥 Hộp thư đến (Giáo viên)",
            "active_page": "message",
        },
    )


# ======================================================
# 📤 2️⃣ Hộp thư đã gửi (Sent)
# ======================================================
@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị hộp thư đã gửi"""
    teacher = current_teacher
    messages = message_service.get_sent_messages(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "message/sent.html",
        {
            "request": request,
            "teacher": teacher,
            "messages": messages,
            "page_title": "📤 Tin nhắn đã gửi (Giáo viên)",
            "active_page": "message",
        },
    )


# ======================================================
# 📨 3️⃣ Xem chi tiết tin nhắn
# ======================================================
@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(
    request: Request,
    message_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xem nội dung chi tiết tin nhắn"""
    teacher = current_teacher
    message = message_service.get_message_detail(db, message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "message/view_message.html",
        {
            "request": request,
            "teacher": teacher,
            "message": message,
            "page_title": "📨 Xem tin nhắn (Giáo viên)",
            "active_page": "message",
        },
    )


# ======================================================
# ✉️ 4️⃣ Soạn tin nhắn mới
# ======================================================
@router.get("/compose", response_class=HTMLResponse)
async def compose_page(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Trang soạn tin nhắn mới"""
    teacher = current_teacher

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "message/compose_message.html",
        {
            "request": request,
            "teacher": teacher,
            "page_title": "✉️ Soạn tin nhắn mới",
            "active_page": "message",
        },
    )


# ======================================================
# 🚀 5️⃣ Gửi tin nhắn (POST) — hỗ trợ file đính kèm
# ======================================================
@router.post("/compose")
async def send_message(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    receiver_id: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile | None = File(None),
):
    """Gửi tin nhắn nội bộ (có thể đính kèm file)"""
    sender = current_teacher

    receiver = (
        db.query(User)
        .filter((User.email == receiver_id) | (User.id == receiver_id))
        .first()
    )
    if not receiver:
        raise HTTPException(status_code=400, detail="Không tìm thấy người nhận trong hệ thống.")

    message_service.send_message(
        db,
        sender_id=sender.id,
        receiver_id=receiver.id,
        content=content,
        attachment=attachment,
    )

    print(f"✅ [Teacher Message] {sender.id} ➜ {receiver.id} ({receiver.email})")

    return RedirectResponse(
        url="/teacher/message/sent",
        status_code=status.HTTP_303_SEE_OTHER
    )
