from sqlalchemy.orm import Session
from app.models.ai_chat_history import AIChatHistory
import uuid
import traceback

# ======================================================
# 💾 Lưu lịch sử chat (chuẩn hóa ENUM & thêm source)
# ======================================================
def save_chat_history(
    db: Session,
    user_id: str,
    message: str,
    response: str = None,
    role: str = "user",
    source: str = "gemini"
):
    """
    Lưu một lượt chat (user hoặc assistant) vào cơ sở dữ liệu.
    - role: 'user' | 'assistant'
    - source: 'gemini' | 'database' | 'system'
    """
    try:
        if not user_id:
            raise ValueError("❌ user_id bị NULL – không thể lưu lịch sử chat")

        # ✅ Đảm bảo role hợp lệ với ENUM trong DB
        if role not in ["user", "assistant"]:
            print(f"⚠️ [AIChat] Role '{role}' không hợp lệ – đổi thành 'user'")
            role = "user"

        history = AIChatHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            role=role,
            message=message,
            response=response,
            model_name=source,  # ✅ Dùng model_name như 'gemini' hoặc 'database'
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        print(f"✅ [AIChat] Đã lưu lịch sử ({role}) từ {source}: {message[:50]}")
        return history

    except Exception as e:
        db.rollback()
        print("💥 [AIChat ERROR] Lỗi khi lưu lịch sử chat:")
        traceback.print_exc()
        print(f"🧩 Chi tiết lỗi: {e}")
        return None


# ======================================================
# 📜 Lấy lịch sử chat
# ======================================================
def get_chat_history(db: Session, user_id: str, limit: int = 20):
    """Lấy lịch sử chat gần nhất của học viên."""
    try:
        return (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == user_id)
            .order_by(AIChatHistory.created_at.asc())  # Hiển thị theo thứ tự hội thoại
            .limit(limit)
            .all()
        )
    except Exception as e:
        print("⚠️ [AIChat] Không thể lấy lịch sử chat:")
        traceback.print_exc()
        print(f"🧩 Chi tiết lỗi: {e}")
        return []


# ======================================================
# 🗑️ Xóa lịch sử chat
# ======================================================
def clear_chat_history(db: Session, user_id: str):
    """Xóa toàn bộ lịch sử chat của học viên."""
    try:
        deleted_count = (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == user_id)
            .delete()
        )
        db.commit()
        print(f"🗑️ [AIChat] Đã xóa {deleted_count} dòng lịch sử chat của user_id={user_id}")
        return deleted_count
    except Exception as e:
        db.rollback()
        print("💥 [AIChat ERROR] Lỗi khi xóa lịch sử chat:")
        traceback.print_exc()
        print(f"🧩 Chi tiết lỗi: {e}")
        return 0
