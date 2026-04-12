"""
==========================================================
🎓 ROUTER – Student Message
SYNC FIXED VERSION
==========================================================
"""

from pathlib import Path
import mimetypes
import traceback

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from starlette import status

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import message_service
from app.models.user import User

router = APIRouter(
    prefix="/student/message",
    tags=["Student - Message"]
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/", response_class=HTMLResponse)
async def inbox(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

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
        return HTMLResponse("Lỗi tải hộp thư đến.", status_code=500)


@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        messages = message_service.get_sent_messages(db, user_id)
        return templates["student"].TemplateResponse(
            "message/sent.html",
            {
                "request": request,
                "messages": messages,
                "page_title": "📤 Tin đã gửi",
                "active_page": "message",
            },
        )
    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải tin đã gửi.", status_code=500)


@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return HTMLResponse("Không tìm thấy tin nhắn.", status_code=404)

        if user_id not in (message.sender_id, message.receiver_id):
            return HTMLResponse("Bạn không có quyền xem.", status_code=403)

        if message.receiver_id == user_id:
            message = message_service.mark_as_read(db, message_id, user_id) or message

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
        return HTMLResponse("Lỗi xem tin nhắn.", status_code=500)


@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        users = db.query(User).filter(User.id != user_id).all()
        return templates["student"].TemplateResponse(
            "message/compose_message.html",
            {
                "request": request,
                "users": users,
                "page_title": "✉️ Soạn tin nhắn",
                "active_page": "message",
            },
        )
    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải trang.", status_code=500)


@router.post("/compose")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(""),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        receiver_key = (receiver_id or "").strip()

        receiver = (
            db.query(User)
            .filter(
                (User.id == receiver_key) |
                (User.email == receiver_key) |
                (User.username == receiver_key)
            )
            .first()
        )

        if not receiver:
            return HTMLResponse("❌ Người nhận không tồn tại.", status_code=400)

        if receiver.id == user_id:
            return HTMLResponse("❌ Không thể gửi tin nhắn cho chính bạn.", status_code=400)

        msg = message_service.send_message(
            db=db,
            sender_id=user_id,
            receiver_id=receiver.id,
            content=content,
            attachment=attachment,
        )

        if not msg:
            return HTMLResponse("❌ Không thể gửi tin nhắn.", status_code=400)

        return RedirectResponse("/student/message/sent", status_code=status.HTTP_303_SEE_OTHER)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi gửi tin.", status_code=500)


@router.get("/download/{message_id}")
async def download_attachment(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        msg = message_service.get_message_detail(db, message_id)
        if not msg:
            return HTMLResponse("Không tìm thấy tin nhắn.", status_code=404)

        if user_id not in (msg.sender_id, msg.receiver_id):
            return HTMLResponse("Bạn không có quyền.", status_code=403)

        if not msg.attachment_url:
            return HTMLResponse("Không có file.", status_code=404)

        file_path = message_service.resolve_attachment_path(msg)
        if not file_path or not file_path.exists():
            return HTMLResponse("File không tồn tại.", status_code=404)

        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            filename=msg.attachment_name or Path(file_path).name,
            media_type=mime,
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải file.", status_code=500)


@router.get("/delete/{message_id}", response_class=HTMLResponse)
async def delete_message_confirm(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return HTMLResponse("Không tìm thấy tin nhắn.", status_code=404)

        if user_id not in (message.sender_id, message.receiver_id):
            return HTMLResponse("Bạn không có quyền.", status_code=403)

        return templates["student"].TemplateResponse(
            "message/delete_confirm.html",
            {
                "request": request,
                "message": message,
                "page_title": "🗑️ Xóa tin nhắn",
                "active_page": "message",
            },
        )
    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi tải trang xóa.", status_code=500)


@router.post("/delete/{message_id}")
async def delete_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        success = message_service.delete_message(db, message_id, user_id)
        if not success:
            return HTMLResponse("Bạn không có quyền xóa.", status_code=403)

        return RedirectResponse("/student/message/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi xóa tin.", status_code=500)