"""
==========================================================
🛒 ROUTER: Student - Cart (SYNC FIX 2026)
==========================================================
"""

from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config.template_config import templates
from app.core.config import get_settings
from app.services.payment.vnpay_service import build_payment_url, verify_secure_hash
import app.services.student.cart_service as cart_service


router = APIRouter(
    prefix="/student/cart",
    tags=["Student - Cart"],
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


# ======================================================
# ⚡ BUY NOW (clear cart -> add 1 item -> checkout page)
# ======================================================
@router.post("/buy-now/{course_id}")
async def buy_now(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    cart_service.clear_cart(db, user_id)
    cart_service.add_to_cart(db, user_id, course_id)
    request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

    return RedirectResponse("/student/cart/checkout", status_code=303)


# ======================================================
# 🛒 View Cart
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    items = cart_service.get_cart(db, user_id)
    subtotal = cart_service.get_cart_total(db, user_id)
    wallet_balance = cart_service.build_checkout_summary(db, user_id)["wallet_balance"]
    request.session["cart_count"] = len(items)

    return templates["student"].TemplateResponse(
        "cart/cart.html",
        {
            "request": request,
            "items": items,
            "subtotal": subtotal,
            "wallet_balance": wallet_balance,
            "page_title": "🛒 Giỏ hàng của bạn",
            "active_page": "cart",
        },
    )


# ======================================================
# ➕ Add To Cart
# ======================================================
@router.get("/add/{course_id}")
async def cart_add(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    result = cart_service.add_to_cart(db, user_id, course_id)

    request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

    if isinstance(result, dict):
        request.session["cart_notice"] = result.get("message")

    if isinstance(result, dict) and result.get("status") in ["success", "exists"]:
        return RedirectResponse("/student/cart/", status_code=303)

    return RedirectResponse("/student/course/", status_code=303)

# ======================================================
# ❌ Remove One Item
# ======================================================
@router.get("/remove/{item_id}")
async def cart_remove(
    request: Request,
    item_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    cart_service.remove_from_cart(db, user_id, item_id)
    request.session["cart_count"] = cart_service.get_cart_count(db, user_id)

    return RedirectResponse("/student/cart", status_code=303)


# ======================================================
# 🧹 Clear Cart
# ======================================================
@router.get("/clear")
async def cart_clear(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    cart_service.clear_cart(db, user_id)
    request.session["cart_count"] = 0

    return RedirectResponse("/student/cart", status_code=303)


# ======================================================
# 🧾 Checkout Page
# ======================================================
@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    coupon_code: str | None = None,
    pay_method: str = "wallet",
    error: str | None = None,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    summary = cart_service.build_checkout_summary(
        db=db,
        user_id=user_id,
        coupon_code=coupon_code,
        payment_method=pay_method,
    )

    if not summary["items"]:
        return RedirectResponse("/student/cart", status_code=303)

    return templates["student"].TemplateResponse(
        "cart/checkout.html",
        {
            "request": request,
            "items": summary["items"],
            "subtotal": summary["subtotal"],
            "discounted": summary["discounted"],
            "discount_amount": summary["discount_amount"],
            "fee": summary["fee"],
            "total_paid": summary["total_paid"],
            "coupon_code": summary["coupon_code"],
            "valid_coupon": summary["valid_coupon"],
            "wallet_balance": summary["wallet_balance"],
            "pay_method": summary["payment_method"],
            "payment_label": summary["payment_label"],
            "error": error,
            "active_page": "cart",
        },
    )


# ======================================================
# 💳 Confirm Checkout
# ======================================================
@router.post("/checkout")
async def cart_checkout(
    request: Request,
    coupon_code: str = Form(""),
    pay_method: str = Form("wallet"),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    pay_method = (pay_method or "wallet").strip().lower()

    result = cart_service.checkout(
        db=db,
        user_id=user_id,
        coupon_code=coupon_code,
        payment_method=pay_method,
    )

    if result.get("status") == "empty":
        request.session["cart_count"] = 0
        return RedirectResponse("/student/cart", status_code=303)

    if pay_method == "vnpay" and result.get("status") == "pending_payment":
        settings = get_settings()

        if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
            return RedirectResponse(
                "/student/cart/checkout?error=Chưa cấu hình VNPay trong file .env",
                status_code=303,
            )

        payment_url = build_payment_url(
            payment_url=settings.VNPAY_PAYMENT_URL,
            tmn_code=settings.VNPAY_TMN_CODE,
            secret_key=settings.VNPAY_HASH_SECRET,
            return_url=settings.VNPAY_RETURN_URL,
            order_id=result["order_id"],
            amount=Decimal(str(result["total_paid"])),
            ip_address=request.client.host if request.client else "127.0.0.1",
            order_info=f"Thanh toan don hang {result['order_id']}",
        )

        return RedirectResponse(payment_url, status_code=303)

    if result.get("status") != "success":
        summary = cart_service.build_checkout_summary(
            db=db,
            user_id=user_id,
            coupon_code=coupon_code,
            payment_method=pay_method,
        )
        return templates["student"].TemplateResponse(
            "cart/checkout.html",
            {
                "request": request,
                "items": summary["items"],
                "subtotal": summary["subtotal"],
                "discounted": summary["discounted"],
                "discount_amount": summary["discount_amount"],
                "fee": summary["fee"],
                "total_paid": summary["total_paid"],
                "coupon_code": summary["coupon_code"],
                "valid_coupon": summary["valid_coupon"],
                "wallet_balance": summary["wallet_balance"],
                "pay_method": summary["payment_method"],
                "payment_label": summary["payment_label"],
                "error": result.get("message", "Thanh toán thất bại."),
                "active_page": "cart",
            },
            status_code=400,
        )

    request.session["cart_count"] = 0
    request.session["last_checkout"] = result

    return RedirectResponse("/student/cart/checkout/success", status_code=303)


@router.get("/vnpay-return")
async def vnpay_return(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    settings = get_settings()
    params = dict(request.query_params)

    if not settings.VNPAY_HASH_SECRET:
        return RedirectResponse(
            "/student/cart/checkout?error=Chưa cấu hình VNPay",
            status_code=303,
        )

    if not verify_secure_hash(params, settings.VNPAY_HASH_SECRET):
        return RedirectResponse(
            "/student/cart/checkout?error=Chữ ký VNPay không hợp lệ",
            status_code=303,
        )

    order_id = params.get("vnp_TxnRef")
    response_code = params.get("vnp_ResponseCode")
    transaction_status = params.get("vnp_TransactionStatus")
    transaction_id = params.get("vnp_TransactionNo", "")
    amount = Decimal(params.get("vnp_Amount", "0")) / Decimal("100")

    if response_code == "00" and transaction_status == "00":
        result = cart_service.confirm_paid_order(
            db=db,
            order_id=order_id,
            amount=amount,
            transaction_id=transaction_id,
            payment_method="vnpay",
        )

        if result.get("status") == "success":
            request.session["cart_count"] = 0
            request.session["last_checkout"] = result
            return RedirectResponse("/student/cart/checkout/success", status_code=303)

        return RedirectResponse(
            f"/student/cart/checkout?error={result.get('message', 'Xác nhận thanh toán thất bại')}",
            status_code=303,
        )

    cart_service.mark_order_failed(db, order_id)

    return RedirectResponse(
        f"/student/cart/checkout?error=Thanh toán VNPay thất bại. Mã lỗi: {response_code}",
        status_code=303,
    )


@router.get("/vnpay-ipn")
async def vnpay_ipn(
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    params = dict(request.query_params)

    if not settings.VNPAY_HASH_SECRET:
        return {"RspCode": "99", "Message": "Missing hash secret"}

    if not verify_secure_hash(params, settings.VNPAY_HASH_SECRET):
        return {"RspCode": "97", "Message": "Invalid checksum"}

    order_id = params.get("vnp_TxnRef")
    response_code = params.get("vnp_ResponseCode")
    transaction_status = params.get("vnp_TransactionStatus")
    transaction_id = params.get("vnp_TransactionNo", "")
    amount = Decimal(params.get("vnp_Amount", "0")) / Decimal("100")

    if response_code == "00" and transaction_status == "00":
        result = cart_service.confirm_paid_order(
            db=db,
            order_id=order_id,
            amount=amount,
            transaction_id=transaction_id,
            payment_method="vnpay",
        )

        if result.get("status") == "success":
            return {"RspCode": "00", "Message": "Confirm Success"}

        return {
            "RspCode": result.get("code", "99"),
            "Message": result.get("message", "Confirm Failed"),
        }

    cart_service.mark_order_failed(db, order_id)

    return {"RspCode": "00", "Message": "Payment failed recorded"}


# ======================================================
# 🎉 Success Page
# ======================================================
@router.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    result = request.session.get("last_checkout")
    if not result:
        return RedirectResponse("/student/cart", status_code=303)

    request.session["last_checkout"] = None

    return templates["student"].TemplateResponse(
        "cart/payment_success.html",
        {
            "request": request,
            "subtotal": result.get("subtotal", 0),
            "discounted": result.get("discounted", 0),
            "discount_amount": result.get("discount_amount", 0),
            "fee": result.get("fee", 0),
            "total": result.get("total_paid", 0),
            "transaction_id": result.get("transaction_id", ""),
            "order_id": result.get("order_id", ""),
            "payment_method": result.get("payment_method", "wallet"),
            "payment_label": result.get("payment_label", "Thanh toán"),
            "wallet_before": result.get("wallet_before", 0),
            "wallet_after": result.get("wallet_after", 0),
            "wallet_delta": result.get("wallet_delta", 0),
            "coupon_code": result.get("coupon_code", ""),
            "demo_gateway": result.get("demo_gateway", False),
            "purchased_courses": result.get("purchased_courses", []),
            "page_title": "Thanh toán thành công",
            "active_page": "cart",
        },
    )
