"""
==========================================================
🎓 ROUTER TỐI ƯU – Student Message (2025)
Tối ưu 100% tốc độ – bảo mật – clean code
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from starlette import status
from pathlib import Path
import mimetypes
import traceback

# SERVICES & CONFIG
from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import message_service
from app.services.student.notification_service import create_notification
from app.models.user import User


router = APIRouter(
    prefix="/student/message",
    tags=["Student - Message"]
)


# ======================================================
# 🛡️ Utility: Check Session
# ======================================================
def require_login(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return user_id


# ======================================================
# 📥 1) Hộp thư đến (Inbox)
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def inbox(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        messages = message_service.get_inbox_messages(db, user_id)

        return templates["student"].TemplateResponse(
            "message/inbox.html",
            {
                "request": request,
                "messages": messages,
                "page_title": "📥 Hộp thư đến",
                "active_page": "message",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải hộp thư đến.", 500)


# ======================================================
# 📤 2) Tin nhắn đã gửi
# ======================================================
@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        messages = message_service.get_sent_messages(db, user_id)

        return templates["student"].TemplateResponse(
            "message/sent.html",
            {
                "request": request,
                "messages": messages,
                "page_title": "📤 Tin nhắn đã gửi",
                "active_page": "message",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải tin nhắn đã gửi.", 500)


# ======================================================
# 📨 3) Xem chi tiết tin nhắn
# ======================================================
@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return HTMLResponse("Không tìm thấy tin nhắn.", 404)

        # Quyền xem
        if user_id not in (message.sender_id, message.receiver_id):
            return HTMLResponse("Bạn không có quyền xem tin này.", 403)

        return templates["student"].TemplateResponse(
            "message/view_message.html",
            {
                "request": request,
                "message": message,
                "page_title": "📨 Xem tin nhắn",
                "active_page": "message",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi xem tin nhắn.", 500)


# ======================================================
# ✉️ 4) Soạn tin mới (GET)
# ======================================================
@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        users = db.query(User).filter(User.id != user_id).all()

        return templates["student"].TemplateResponse(
            "message/compose_message.html",
            {
                "request": request,
                "users": users,
                "page_title": "✉️ Soạn tin nhắn mới",
                "active_page": "message",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải trang soạn tin.", 500)


# ======================================================
# 📨 5) Gửi tin nhắn (POST)
# ======================================================
@router.post("/compose")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        # Tìm người nhận theo id / email / username
        receiver = (
            db.query(User)
            .filter(
                (User.id == receiver_id)
                | (User.email == receiver_id)
                | (User.username == receiver_id)
            )
            .first()
        )

        if not receiver:
            return HTMLResponse("Không tìm thấy người nhận.", 400)

        # Gửi tin
        msg = message_service.send_message(
            db=db,
            sender_id=user_id,
            receiver_id=receiver.id,
            content=content.strip(),
            attachment=attachment,
        )

        # 🔔 Bắn thông báo
        create_notification(
            db=db,
            user_id=receiver.id,
            title="📩 Tin nhắn mới",
            message=f"Bạn nhận được tin nhắn từ người dùng {user_id}",
            notification_type="message",
            link_url=f"/student/message/view/{msg.id}",
        )

        return RedirectResponse("/student/message/sent", 303)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi gửi tin nhắn.", 500)


# ======================================================
# ⬇️ 6) Tải file đính kèm
# ======================================================
@router.get("/download/{message_id}")
async def download_attachment(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return HTMLResponse("Không tìm thấy tin nhắn.", 404)

        if user_id not in (message.sender_id, message.receiver_id):
            return HTMLResponse("Bạn không có quyền tải file.", 403)

        if not message.attachment_url:
            return HTMLResponse("Tin nhắn không có file.", 404)

        file_path = Path(message.attachment_url)
        if not file_path.exists():
            return HTMLResponse("File không tồn tại.", 404)

        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"

        return FileResponse(
            path=file_path,
            filename=message.attachment_name or file_path.name,
            media_type=mime,
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải file đính kèm.", 500)


# ======================================================
# 🗑️ 7) Xóa tin nhắn
# ======================================================
@router.get("/delete/{message_id}")
async def delete_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        success = message_service.delete_message(db, message_id, user_id)
        if not success:
            return HTMLResponse("Bạn không có quyền xóa tin nhắn này.", 403)

        return RedirectResponse("/student/message/", 303)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi xóa tin nhắn.", 500)
