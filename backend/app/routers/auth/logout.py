from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

# ============================================================
# 🚀 Router
# ============================================================
logout_router = APIRouter(prefix="/auth", tags=["Auth"])

# ============================================================
# 🔒 Đăng xuất người dùng
# ============================================================
@logout_router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """
    ✅ Xóa session người dùng và chuyển hướng về trang đăng nhập.
    """
    try:
        if hasattr(request, "session") and request.session:
            request.session.clear()
            print("✅ Phiên người dùng đã được xóa.")
        else:
            print("⚠️ Không tìm thấy session để xóa.")
    except Exception as e:
        print(f"❌ Lỗi khi đăng xuất: {e}")

    # 👉 Chuyển hướng về trang đăng nhập
    return RedirectResponse(url="/auth/login", status_code=303)
