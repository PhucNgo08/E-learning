"""
==========================================================
🛒 ROUTER: Student - Cart (PREMIUM 2025 - FINAL 100%)
Tương thích FULL cart_service FINAL + course_service FINAL
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import traceback

from app.database.connection import get_db
from app.config.template_config import templates

import app.services.student.cart_service as cart_service


router = APIRouter(
    prefix="/student/cart",
    tags=["Student - Cart"]
)


# ======================================================
# 🛒 (1) Xem GIỎ HÀNG
# ======================================================
@router.get("/", response_class=HTMLResponse, name="student_cart_index")
async def cart_page(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        items = cart_service.get_cart(db, user_id)
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
        print("❌ [Cart][View] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải giỏ hàng.", status_code=500)


# ======================================================
# ➕ (2) Thêm khóa học vào giỏ
# ======================================================
@router.get("/add/{course_id}", name="student_cart_add")
async def cart_add(request: Request, course_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        cart_service.add_to_cart(db, user_id, course_id)
        request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

        return RedirectResponse("/student/cart", 303)

    except Exception as e:
        print("❌ [Cart][Add] Lỗi:", e)
        traceback.print_exc()
        return RedirectResponse("/student/course", 303)


# ======================================================
# ❌ (3) Xóa 1 item khỏi giỏ hàng
# ======================================================
@router.get("/remove/{item_id}", name="student_cart_remove")
async def cart_remove(request: Request, item_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        cart_service.remove_from_cart(db, user_id, item_id)
        request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

        return RedirectResponse("/student/cart", 303)

    except Exception as e:
        print("❌ [Cart][Remove] Lỗi:", e)
        traceback.print_exc()
        return RedirectResponse("/student/cart", 303)


# ======================================================
# 🧹 (4) Xóa toàn bộ giỏ hàng
# ======================================================
@router.get("/clear", name="student_cart_clear")
async def cart_clear(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        cart_service.clear_cart(db, user_id)
        request.session["cart_count"] = 0

        return RedirectResponse("/student/cart", 303)

    except Exception as e:
        print("❌ [Cart][Clear] Lỗi:", e)
        traceback.print_exc()
        return RedirectResponse("/student/cart", 303)


# ======================================================
# 🧾 (5) TRANG CHECKOUT
# ======================================================
@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: Session = Depends(get_db)):

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
            "active_page": "courses",
        },
    )


# ======================================================
# 💳 (6) Checkout xử lý thanh toán
# ======================================================
@router.post("/checkout", name="student_cart_checkout")
async def cart_checkout(
    request: Request,
    coupon_code: str = Form(None),
    pay_method: str = Form("momo"),
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

        request.session["cart_count"] = 0

        return RedirectResponse(
            f"/student/cart/checkout/success?"
            f"subtotal={result['subtotal']}"
            f"&discounted={result['discounted']}"
            f"&fee={result['fee']}"
            f"&total={result['total_paid']}"
            f"&trans={result['transaction_id']}"
            f"&order_id={result['order_id']}",
            status_code=303,
        )

    except Exception as e:
        db.rollback()
        print("❌ [Cart][Checkout] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi thanh toán.", status_code=500)


# ======================================================
# 🎉 (7) PAYMENT SUCCESS PAGE
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
):

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
        },
    )
