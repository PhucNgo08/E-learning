"""
==========================================================
🎓 ROUTER: Student - Message
Hoàn thiện đầy đủ chức năng tin nhắn nội bộ cho học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from starlette import status
from pathlib import Path
import traceback

# ✅ Import config & service
from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import message_service
from app.models.user import User


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
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
    """Hiển thị hộp thư đến."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

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
    except Exception as e:
        print("❌ [Message][Inbox] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải hộp thư đến.</h4>", status_code=500)


# ======================================================
# 📤 2️⃣ Hộp thư đã gửi (Sent)
# ======================================================
@router.get("/sent", response_class=HTMLResponse)
async def sent_messages(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tin nhắn đã gửi."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

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
    except Exception as e:
        print("❌ [Message][Sent] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải tin nhắn đã gửi.</h4>", status_code=500)


# ======================================================
# 📨 3️⃣ Xem chi tiết tin nhắn
# ======================================================
@router.get("/view/{message_id}", response_class=HTMLResponse)
async def view_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết 1 tin nhắn."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy tin nhắn."},
                status_code=404,
            )

        # 🔒 Chỉ người gửi hoặc người nhận mới được xem
        if message.sender_id != user_id and message.receiver_id != user_id:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xem tin nhắn này."},
                status_code=403,
            )

        return templates["student"].TemplateResponse(
            "message/view_message.html",
            {
                "request": request,
                "message": message,
                "page_title": "📨 Xem tin nhắn",
                "active_page": "message",
            },
        )
    except Exception as e:
        print("❌ [Message][View] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem tin nhắn.</h4>", status_code=500)


# ======================================================
# ✉️ 4️⃣ Soạn tin nhắn mới (GET)
# ======================================================
@router.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request, db: Session = Depends(get_db)):
    """Hiển thị form soạn tin nhắn + danh sách người dùng."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

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
    except Exception as e:
        print("❌ [Message][ComposePage] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải trang soạn tin nhắn.</h4>", status_code=500)


# ======================================================
# 📨 5️⃣ Gửi tin nhắn (POST)
# ======================================================
@router.post("/compose")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Gửi tin nhắn (hỗ trợ file đính kèm)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        receiver = (
            db.query(User)
            .filter((User.email == receiver_id) | (User.id == receiver_id))
            .first()
        )

        if not receiver:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy người nhận trong hệ thống."},
                status_code=400,
            )

        message_service.send_message(
            db,
            sender_id=user_id,
            receiver_id=receiver.id,
            content=content.strip(),
            attachment=attachment,
        )

        print(f"✅ [Message][Send] {user_id} ➜ {receiver.id}")
        return RedirectResponse(
            url="/student/message/sent",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        db.rollback()
        print("❌ [Message][Send] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi gửi tin nhắn.</h4>", status_code=500)


# ======================================================
# ⬇️ 6️⃣ Tải file đính kèm
# ======================================================
@router.get("/download/{message_id}")
async def download_attachment(request: Request, message_id: str, db: Session = Depends(get_db)):
    """Tải file đính kèm (chỉ người gửi hoặc nhận)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        message = message_service.get_message_detail(db, message_id)
        if not message:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy tin nhắn."},
                status_code=404,
            )

        if message.sender_id != user_id and message.receiver_id != user_id:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền tải file này."},
                status_code=403,
            )

        if not message.attachment_url:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Tin nhắn này không có tệp đính kèm."},
                status_code=404,
            )

        file_path = Path(message.attachment_url)
        if not file_path.exists():
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ File không còn tồn tại trên hệ thống."},
                status_code=404,
            )

        print(f"⬇️ [Message][Download] User={user_id} tải {file_path.name}")
        return FileResponse(
            path=file_path,
            filename=message.attachment_name or file_path.name,
            media_type="application/octet-stream",
        )

    except Exception as e:
        print("❌ [Message][Download] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải file đính kèm.</h4>", status_code=500)


# ======================================================
# 🗑️ 7️⃣ Xóa tin nhắn (chỉ chủ sở hữu)
# ======================================================
@router.get("/delete/{message_id}", response_class=HTMLResponse)
async def delete_message(request: Request, message_id: str, db: Session = Depends(get_db)):
    """Xóa tin nhắn (nếu là người gửi hoặc người nhận)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        success = message_service.delete_message(db, message_id, user_id)
        if not success:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Bạn không có quyền xóa tin nhắn này."},
                status_code=403,
            )

        print(f"🗑️ [Message][Delete] User={user_id} xóa message={message_id}")
        return RedirectResponse(
            url="/student/message/",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        db.rollback()
        print("❌ [Message][Delete] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xóa tin nhắn.</h4>", status_code=500)
