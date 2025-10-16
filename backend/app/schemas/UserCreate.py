from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str

class UserUpdate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str = None  # Mật khẩu có thể bỏ qua khi cập nhật

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str

    class Config:
        from_attributes = True
