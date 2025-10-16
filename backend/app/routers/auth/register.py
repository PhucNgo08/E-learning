from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas import UserResponse  # Đảm bảo import đúng
from fastapi import Depends
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session  # Import Session
from app.db.session import get_db  # Import get_db để lấy Session
from app.models.user import User
from app.schemas import UserResponse  # Đảm bảo import đúng 
from fastapi.templating import Jinja2Templates  # Import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse  # Import HTMLResponse

# Khởi tạo templates để render HTML
templates = Jinja2Templates(directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/auth")
register_router = APIRouter()  # Đảm bảo sử dụng đúng biến router

# Định nghĩa route cho trang đăng ký (register page)
@register_router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})
# Route để lấy thông tin user theo ID
@register_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    # Tìm user trong cơ sở dữ liệu
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
