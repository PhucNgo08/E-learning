# app/dependencies/auth.py

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User

# ==============================
# Dependency: lấy user hiện tại
# ==============================
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    ✅ Lấy người dùng hiện tại dựa trên session user_id.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn chưa đăng nhập."
        )

    # Truy vấn user theo ID (chắc chắn duy nhất)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    return user



# ==============================
# Dependency: chỉ cho phép học viên
# ==============================
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


# ==============================
# Dependency: chỉ cho phép giáo viên
# ==============================
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


# ==============================
# Dependency: chỉ cho phép admin
# ==============================
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
