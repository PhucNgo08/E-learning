"""
==========================================================
🎓 ROUTER: Student - Message
Quản lý hệ thống tin nhắn nội bộ cho học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from pathlib import Path

# ✅ Import config & service
from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import message_service
from app.models.user import User


router = APIRouter(
    prefix="/student/message",
    tags=["Student - Message"]
)


# ======================================================
# 📥 1️⃣ Hộp thư đến (Inbox)
# ======================================================
@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def inbox(request: Request, db: Session = Depends(get_db)):
    """Hiển thị hộp thư đến"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

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


# ======================================================
# 📤 2️⃣ Hộp thư đã gửi (Sent)
# ======================================================
@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(request: Request, db: Session = Depends(get_db)):
    """Hiển thị hộp thư đã gửi"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

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


# ======================================================
# 📨 3️⃣ Xem chi tiết tin nhắn
# ======================================================
@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết tin nhắn"""
    message = message_service.get_message_detail(db, message_id)
    if not message:
        return HTMLResponse("❌ Không tìm thấy tin nhắn.", status_code=404)

    return templates["student"].TemplateResponse(
        "message/view_message.html",
        {
            "request": request,
            "message": message,
            "page_title": "📨 Xem tin nhắn",
            "active_page": "message",
        },
    )


# ======================================================
# ✉️ 4️⃣ Soạn tin nhắn mới
# ======================================================
@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request):
    """Hiển thị form soạn tin nhắn"""
    return templates["student"].TemplateResponse(
        "message/compose_message.html",
        {
            "request": request,
            "page_title": "✉️ Soạn tin nhắn mới",
            "active_page": "message",
        },
    )


# ======================================================
# 📨 5️⃣ Gửi tin nhắn (POST) — có hỗ trợ file đính kèm
# ======================================================
@router.post("/compose")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile = File(None),  # 📎 File tùy chọn
    db: Session = Depends(get_db)
):
    """Gửi tin nhắn nội bộ — nhập Email hoặc ID người nhận"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🔍 Tìm người nhận
    receiver = (
        db.query(User)
        .filter((User.email == receiver_id) | (User.id == receiver_id))
        .first()
    )

    if not receiver:
        return HTMLResponse("<h4>❌ Không tìm thấy người nhận trong hệ thống.</h4>", status_code=400)

    # ✅ Gửi tin nhắn qua service (kèm file)
    message_service.send_message(
        db,
        sender_id=user_id,
        receiver_id=receiver.id,
        content=content,
        attachment=attachment
    )

    print(f"✅ [send_message] {user_id} ➜ {receiver.id} ({receiver.email})")

    return RedirectResponse(
        url="/student/message/sent",
        status_code=status.HTTP_303_SEE_OTHER
    )
