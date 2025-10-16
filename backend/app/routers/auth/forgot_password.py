# app/routers/auth/forgot_password.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import services, database
from app.routers.auth.utils import send_reset_email, generate_reset_token

router = APIRouter(prefix="/auth", tags=["Auth"])  # ✅ Quan trọng!

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/auth"
)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password", response_class=JSONResponse)
async def forgot_password(email: str = Form(...), db: Session = Depends(database.get_db)):
    user = services.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại trong hệ thống")

    token = generate_reset_token(email)
    reset_link = f"http://localhost:8000/auth/reset-password?token={token}"
    send_reset_email(email, reset_link)
    return {"message": "Hướng dẫn đặt lại mật khẩu đã được gửi qua email."}
