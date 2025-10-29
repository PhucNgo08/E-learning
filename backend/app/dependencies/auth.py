"""
==========================================================
🔐 AUTH DEPENDENCIES
Xác thực & phân quyền người dùng cho toàn hệ thống
==========================================================
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User


# =====================================================
# 🧠 Lấy người dùng hiện tại từ Session
# =====================================================
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    ✅ Trả về thông tin người dùng hiện tại dựa trên session.
    - Kiểm tra user_id trong session
    - Truy vấn DB để lấy User
    - Tự động đồng bộ thông tin cơ bản vào session
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn chưa đăng nhập."
        )

    # 🔍 Truy vấn user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng."
        )

    # 🔁 Đồng bộ session
    if not request.session.get("user_full_name") or request.session["user_full_name"] != user.full_name:
        request.session["user_full_name"] = user.full_name
    if not request.session.get("user_role") or request.session["user_role"] != user.role:
        request.session["user_role"] = user.role
    if not request.session.get("user_avatar") or request.session["user_avatar"] != user.avatar_url:
        request.session["user_avatar"] = user.avatar_url or "/uploads/avatars/default-avatar.png"

    return user


# =====================================================
# 🎓 Chỉ cho phép Học viên
# =====================================================
def get_current_student(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    user = get_current_user(request, db)
    if user.role.lower() != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập (chỉ học viên)."
        )
    return user


# =====================================================
# 👨‍🏫 Chỉ cho phép Giáo viên
# =====================================================
def get_current_teacher(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    user = get_current_user(request, db)
    if user.role.lower() != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập (chỉ giáo viên)."
        )
    return user


# =====================================================
# 🛠️ Chỉ cho phép Quản trị viên
# =====================================================
def get_current_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    user = get_current_user(request, db)
    if user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập (chỉ admin)."
        )
    return user
