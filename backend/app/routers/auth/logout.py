from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

logout_router = APIRouter(prefix="/auth", tags=["Auth"])

@logout_router.get("/logout")
async def logout(request: Request):
    """Xóa session và chuyển hướng về trang đăng nhập."""
    if request.session:
        request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
