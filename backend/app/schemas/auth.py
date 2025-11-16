# app/schemas/auth.py

from pydantic import BaseModel
from typing import Optional


# =======================================
# 🔐 Dùng để trả token đơn giản
# =======================================
class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =======================================
# 🔐 Token + thông tin người dùng
# =======================================
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    user_id: str
    username: str
    role: str


# =======================================
# 🔐 Dùng để giải mã token trong dependency
# =======================================
class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None


# =======================================
# 🔄 Nếu bạn dùng refresh token (optional)
# =======================================
class RefreshToken(BaseModel):
    refresh_token: str
