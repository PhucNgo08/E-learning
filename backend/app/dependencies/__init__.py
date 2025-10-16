# app/dependencies/__init__.py
from fastapi import Depends, Request, HTTPException, status

def get_current_user_id(request: Request):
    """
    ✅ Lấy user_id từ session (sau khi đăng nhập)
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để truy cập nội dung này."
        )
    return user_id
