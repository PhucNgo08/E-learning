# app/schemas/login.py

from pydantic import BaseModel
from typing import Optional


# ===========================
# 🔐 Request khi đăng nhập
# ===========================
class LoginRequest(BaseModel):
    username: str
    password: str


# ===========================
# 🔐 Token trả về sau đăng nhập
# ===========================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===========================
# 🔐 Token + Thông tin user
# ===========================
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


# ===========================
# 🔐 Dùng để decode token
# ===========================
class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
