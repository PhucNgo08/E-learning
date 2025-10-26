"""
📊 User Statistics Service
Thống kê người dùng theo vai trò, trạng thái, và lần đăng nhập gần nhất.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User


def get_user_statistics(db: Session):
    """Thống kê số lượng người dùng theo role, trạng thái và lần đăng nhập gần nhất."""
    stats = {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "by_role": {},
        "by_status": {},
        "recent_login": []
    }

    # =====================================================
    # 📘 1️⃣ Thống kê theo vai trò (role)
    # =====================================================
    try:
        roles = (
            db.query(User.role, func.count(User.id))
            .group_by(User.role)
            .all()
        )
        stats["by_role"] = {r or "Không xác định": c for r, c in roles}
    except Exception as e:
        print(f"⚠️ Lỗi khi thống kê role: {e}")
        stats["by_role"] = {}

    # =====================================================
    # 📗 2️⃣ Thống kê theo trạng thái (status)
    # =====================================================
    try:
        statuses = (
            db.query(User.status, func.count(User.id))
            .group_by(User.status)
            .all()
        )
        stats["by_status"] = {s or "unknown": c for s, c in statuses}
    except Exception as e:
        print(f"⚠️ Lỗi khi thống kê status: {e}")
        stats["by_status"] = {}

    # =====================================================
    # 📙 3️⃣ 5 người đăng nhập gần nhất
    # =====================================================
    try:
        recent = (
            db.query(User.full_name, User.last_login)
            .filter(User.last_login.isnot(None))
            .order_by(User.last_login.desc())
            .limit(5)
            .all()
        )
        stats["recent_login"] = [
            {
                "name": n,
                "time": t.strftime("%H:%M %d/%m/%Y") if t else "Chưa đăng nhập"
            }
            for n, t in recent
        ]
    except Exception as e:
        print(f"⚠️ Lỗi khi lấy danh sách đăng nhập gần nhất: {e}")
        stats["recent_login"] = []

    return stats
