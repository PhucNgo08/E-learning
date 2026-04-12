from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.schemas import UserResponse
from app.config.template_config import get_template_by_path
from fastapi import Form
from fastapi.responses import RedirectResponse
from app.models.user_profile import UserProfile
from app.services.common.password_service import hash_password
register_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@register_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Hiển thị trang đăng ký tài khoản."""
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "register.html",
        {"request": request, "page_title": "📝 Đăng ký tài khoản"},
    )


@register_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """API lấy thông tin chi tiết người dùng theo UUID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ Không tìm thấy người dùng.")
    return user
@register_router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    tpl = get_template_by_path(request.url.path)

    existing = (
        db.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )
    if existing:
        return tpl.TemplateResponse(
            "register.html",
            {
                "request": request,
                "page_title": "📝 Đăng ký tài khoản",
                "error": "Tên đăng nhập hoặc email đã tồn tại.",
            },
            status_code=400,
        )

    try:
        new_user = User(
            username=username.strip(),
            email=email.strip(),
            password_hash=hash_password(password),
            status="active",
        )
        db.add(new_user)
        db.flush()

        profile = UserProfile(
            user_id=new_user.id,
            full_name=full_name.strip(),
        )
        db.add(profile)
        db.commit()

        return RedirectResponse(url="/auth/login", status_code=303)

    except Exception:
        db.rollback()
        return tpl.TemplateResponse(
            "register.html",
            {
                "request": request,
                "page_title": "📝 Đăng ký tài khoản",
                "error": "Không thể tạo tài khoản.",
            },
            status_code=500,
        )