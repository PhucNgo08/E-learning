"""
==========================================================
🛒 ROUTER: Student - Cart (PREMIUM 2025 - WALLET EDITION)
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import uuid
import traceback

from app.database.connection import get_db
from app.config.template_config import templates

import app.services.student.cart_service as cart_service
from app.services.wallet_service import get_balance  # ⭐ NEW


router = APIRouter(
    prefix="/student/cart",
    tags=["Student - Cart"]
)

# ======================================================
# ⚡ BUY NOW (Add → Redirect Checkout)
# ======================================================
@router.post("/buy-now/{course_id}")
async def buy_now(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    # Xóa giỏ → thêm 1 item duy nhất
    cart_service.clear_cart(db, user_id)
    cart_service.add_to_cart(db, user_id, course_id)

    request.session["cart_count"] = 1

    return RedirectResponse("/student/cart/checkout", 303)


# ======================================================
# 🛒 Xem giỏ hàng
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        items = cart_service.get_cart(db, user_id)

        # Nếu giỏ trống
        if not items:
            request.session["cart_count"] = 0
            return templates["student"].TemplateResponse(
                "cart/cart_empty.html",
                {
                    "request": request,
                    "page_title": "🛒 Giỏ hàng trống",
                    "active_page": "courses",
                },
            )

        subtotal = cart_service.get_cart_total(db, user_id)
        request.session["cart_count"] = len(items)

        return templates["student"].TemplateResponse(
            "cart/cart.html",
            {
                "request": request,
                "items": items,
                "subtotal": subtotal,
                "page_title": "🛒 Giỏ hàng của bạn",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("❌ [Cart View] Lỗi:", e)
        return HTMLResponse("Lỗi tải giỏ hàng.", status_code=500)


# ======================================================
# ➕ Thêm 1 khóa học vào giỏ
# ======================================================
@router.get("/add/{course_id}")
async def cart_add(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        cart_service.add_to_cart(db, user_id, course_id)
        request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

        return RedirectResponse("/student/cart", 303)

    except Exception as e:
        print("❌ [Cart Add] Lỗi:", e)
        return RedirectResponse("/student/course", 303)


# ======================================================
# ❌ Xóa 1 item khỏi giỏ
# ======================================================
@router.get("/remove/{item_id}")
async def cart_remove(
    request: Request,
    item_id: str,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    cart_service.remove_from_cart(db, user_id, item_id)
    request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

    return RedirectResponse("/student/cart", 303)


# ======================================================
# 🧹 Xóa toàn bộ giỏ
# ======================================================
@router.get("/clear")
async def cart_clear(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    cart_service.clear_cart(db, user_id)
    request.session["cart_count"] = 0

    return RedirectResponse("/student/cart", 303)


# ======================================================
# 🧾 Trang thanh toán
# ======================================================
@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    error: str = None,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    items = cart_service.get_cart(db, user_id)
    if not items:
        return RedirectResponse("/student/cart", 303)

    subtotal = cart_service.get_cart_total(db, user_id)

    return templates["student"].TemplateResponse(
        "cart/checkout.html",
        {
            "request": request,
            "items": items,
            "subtotal": subtotal,
            "error": error,   # Hiển thị lỗi ví không đủ
            "active_page": "courses",
        },
    )


# ======================================================
# 💳 TIẾN HÀNH THANH TOÁN (Wallet)
# ======================================================
@router.post("/checkout")
async def cart_checkout(
    request: Request,
    coupon_code: str = Form(None),
    pay_method: str = Form("wallet"),  # mặc định ví
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        result = cart_service.checkout(
            db=db,
            user_id=user_id,
            coupon_code=coupon_code,
            payment_method=pay_method
        )

        # 🧹 Clear giỏ
        request.session["cart_count"] = 0  

        # 💾 Lưu danh sách khóa học để hiển thị ở trang success
        request.session["purchased_courses"] = result.get("purchased_courses", [])

        return RedirectResponse(
            f"/student/cart/checkout/success?"
            f"subtotal={result['subtotal']}"
            f"&discounted={result['discounted']}"
            f"&fee={result['fee']}"
            f"&total={result['total_paid']}"
            f"&trans={result['transaction_id']}"
            f"&order_id={result['order_id']}",
            303,
        )

    except Exception as e:

        # Lỗi ví không đủ tiền
        if "không đủ" in str(e).lower():
            return RedirectResponse(
                f"/student/cart/checkout?error={str(e)}",
                status_code=303
            )

        print("❌ [Checkout] Lỗi:", e)
        return HTMLResponse(f"Lỗi thanh toán: {str(e)}", status_code=500)


# ======================================================
# 🎉 Payment Success Page (Wallet)
# ======================================================
@router.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(
    request: Request,
    subtotal: float = 0,
    discounted: float = 0,
    fee: float = 0,
    total: float = 0,
    trans: str = "",
    order_id: str = "",
    db: Session = Depends(get_db),
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    # 💰 Số dư sau giao dịch
    wallet_after = get_balance(db, user_id)

    # 💸 Tổng đã trừ từ ví (total đã là discounted + fee)
    wallet_delta = float(total) if total else 0.0
    wallet_before = wallet_after + wallet_delta

    # 🎓 Khóa học đã kích hoạt từ session
    purchased_courses = request.session.get("purchased_courses") or []
    # Xóa cho sạch, tránh reuse
    request.session["purchased_courses"] = []

    return templates["student"].TemplateResponse(
        "cart/payment_success.html",
        {
            "request": request,
            "subtotal": subtotal,
            "discounted": discounted,
            "fee": fee,
            "total": total,
            "transaction_id": trans,
            "order_id": order_id,
            "page_title": "Thanh toán thành công",

            # 💰 Info ví
            "wallet_before": wallet_before,
            "wallet_after": wallet_after,
            "wallet_delta": wallet_delta,

            "purchased_courses": purchased_courses,
            "active_page": "courses",
        },
    )
