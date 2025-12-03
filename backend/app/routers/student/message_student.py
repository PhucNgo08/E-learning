"""
==========================================================
🎓 ROUTER – Student Message (2025 FINAL FIX)
Tối ưu hóa – Không tạo thông báo 2 lần – Clean code nhất
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
from app.models.user import User

router = APIRouter(
    prefix="/student/message",
    tags=["Student - Message"]
)

# ======================================================
# 🛡️ Utility: Check login
# ======================================================
def require_login(request: Request):
    return request.session.get("user_id")


# ======================================================
# 📥 1) Hộp thư đến
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def inbox(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        messages = message_service.get_inbox_messages(db, user_id)
        return templates["student"].TemplateResponse(
            "message/inbox.html",
            {"request": request, "messages": messages, "page_title": "📥 Hộp thư đến", "active_page": "message"},
        )
    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải hộp thư đến.", 500)


# ======================================================
# 📤 2) Tin nhắn đã gửi
# ======================================================
@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        messages = message_service.get_sent_messages(db, user_id)
        return templates["student"].TemplateResponse(
            "message/sent.html",
            {"request": request, "messages": messages, "page_title": "📤 Tin đã gửi", "active_page": "message"},
        )
    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải tin đã gửi.", 500)


# ======================================================
# 📨 3) Xem chi tiết
# ======================================================
@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(request: Request, message_id: str, db: Session = Depends(get_db)):

    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return HTMLResponse("Không tìm thấy tin nhắn.", 404)

        if user_id not in (message.sender_id, message.receiver_id):
            return HTMLResponse("Bạn không có quyền xem.", 403)

        return templates["student"].TemplateResponse(
            "message/view_message.html",
            {"request": request, "message": message, "page_title": "📨 Xem tin nhắn", "active_page": "message"},
        )

    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi xem tin nhắn.", 500)


# ======================================================
# ✉️ 4) Trang soạn tin
# ======================================================
@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        users = db.query(User).filter(User.id != user_id).all()
        return templates["student"].TemplateResponse(
            "message/compose_message.html",
            {"request": request, "users": users, "page_title": "✉️ Soạn tin nhắn", "active_page": "message"},
        )
    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải trang.", 500)


# ======================================================
# 📨 5) Gửi tin nhắn (FIX: hỗ trợ Email + Username + ID)
# ======================================================
@router.post("/compose")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(""),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        # 🎯 TÌM NGƯỜI NHẬN THEO: ID | Email | Username
        receiver = (
            db.query(User)
            .filter(
                (User.id == receiver_id) |
                (User.email == receiver_id) |
                (User.username == receiver_id)
            )
            .first()
        )

        if not receiver:
            return HTMLResponse("❌ Người nhận không tồn tại.", 400)

        msg = message_service.send_message(
            db=db,
            sender_id=user_id,
            receiver_id=receiver.id,
            content=content,
            attachment=attachment,
        )

        if not msg:
            return HTMLResponse("❌ Không thể gửi tin nhắn.", 400)

        return RedirectResponse("/student/message/sent", status.HTTP_303_SEE_OTHER)

    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi gửi tin.", 500)


# ======================================================
# ⬇️ 6) Download file
# ======================================================
@router.get("/download/{message_id}")
async def download_attachment(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        msg = message_service.get_message_detail(db, message_id)
        if not msg:
            return HTMLResponse("Không tìm thấy tin nhắn.", 404)

        if user_id not in (msg.sender_id, msg.receiver_id):
            return HTMLResponse("Bạn không có quyền.", 403)

        if not msg.attachment_url:
            return HTMLResponse("Không có file.", 404)

        file_path = Path(msg.attachment_url.lstrip("/"))
        if not file_path.exists():
            return HTMLResponse("File không tồn tại.", 404)

        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"

        return FileResponse(path=file_path, filename=msg.attachment_name, media_type=mime)

    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải file.", 500)


# ======================================================
# 🗑️ 7) Xóa tin nhắn
# ======================================================
@router.get("/delete/{message_id}")
async def delete_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse("/auth/login")

    try:
        success = message_service.delete_message(db, message_id, user_id)
        if not success:
            return HTMLResponse("Bạn không có quyền xóa.", 403)

        return RedirectResponse("/student/message/", status.HTTP_303_SEE_OTHER)

    except:
        traceback.print_exc()
        return HTMLResponse("Lỗi xóa tin.", 500)
