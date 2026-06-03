"""
==========================================================
🛒 ROUTER: Student - Cart
Quản lý giỏ hàng sinh viên
Fix:
- Nhận đúng session role: user_role hoặc role
- Route add-to-cart trả JSON khi gọi bằng fetch()
- Cập nhật cart_count trong session
- FIX VNPay: pending_payment sẽ chuyển sang cổng VNPay, không render lại checkout
- Có route vnpay-pay, vnpay-return, vnpay-ipn
==========================================================
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode, quote_plus

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config.template_config import templates
from app.models.order import Order
import app.services.student.cart_service as cart_service


router = APIRouter(
    prefix="/student/cart",
    tags=["Student - Cart"],
)


# ======================================================
# COMMON
# ======================================================
def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")

    if not user_id or role != "student":
        return None

    return user_id


def wants_json_response(request: Request) -> bool:
    accept = request.headers.get("accept") or ""
    requested_with = request.headers.get("x-requested-with") or ""

    return (
        "application/json" in accept.lower()
        or requested_with.lower() == "xmlhttprequest"
    )


def _get_setting(name: str, default: str = "") -> str:
    """
    Lấy cấu hình từ app.core.config hoặc biến môi trường.
    Hỗ trợ nhiều tên để tránh lệch config giữa các phiên bản.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()

        if hasattr(settings, name):
            value = getattr(settings, name)
            if value is not None:
                return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _get_first_setting(names: list[str], default: str = "") -> str:
    for name in names:
        value = _get_setting(name, "")
        if value:
            return value
    return default


def _format_vnpay_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _vnpay_sign(params: dict, secret_key: str) -> str:
    """
    Tạo chữ ký VNPay.
    Dùng cùng logic cho tạo URL và verify return/ipn.
    """
    filtered = {
        key: value
        for key, value in params.items()
        if value is not None
        and value != ""
        and key not in ("vnp_SecureHash", "vnp_SecureHashType")
    }

    sorted_items = sorted(filtered.items())
    hash_data = urlencode(sorted_items, quote_via=quote_plus)

    return hmac.new(
        secret_key.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def _verify_vnpay_signature(params: dict) -> bool:
    secret_key = _get_first_setting(
        ["VNPAY_HASH_SECRET", "VNPAY_HASH_SECRET_KEY", "VNPAY_SECRET_KEY"],
        "",
    )

    if not secret_key:
        return False

    received_hash = params.get("vnp_SecureHash") or ""
    calculated_hash = _vnpay_sign(params, secret_key)

    return received_hash.lower() == calculated_hash.lower()


def _build_vnpay_payment_url(
    request: Request,
    order: Order,
    client_ip: str = "127.0.0.1",
) -> str:
    """
    Tạo URL thanh toán VNPay Sandbox.
    """
    vnpay_url = _get_first_setting(
        ["VNPAY_PAYMENT_URL", "VNPAY_URL", "VNPAY_PAY_URL"],
        "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    )

    tmn_code = _get_first_setting(
        ["VNPAY_TMN_CODE", "VNPAY_TMNCODE", "VNP_TMNCODE"],
        "",
    )

    secret_key = _get_first_setting(
        ["VNPAY_HASH_SECRET", "VNPAY_HASH_SECRET_KEY", "VNPAY_SECRET_KEY"],
        "",
    )

    return_url = _get_first_setting(
        ["VNPAY_RETURN_URL"],
        str(request.url_for("student_cart_vnpay_return")),
    )

    if not tmn_code:
        raise RuntimeError("Thiếu cấu hình VNPAY_TMN_CODE hoặc VNPAY_TMNCODE.")

    if not secret_key:
        raise RuntimeError("Thiếu cấu hình VNPAY_HASH_SECRET.")

    now = datetime.utcnow() + timedelta(hours=7)

    amount = int(Decimal(str(order.total_amount or 0)) * 100)

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": tmn_code,
        "vnp_Amount": str(amount),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": order.id,
        "vnp_OrderInfo": f"Thanh toan khoa hoc {order.id}",
        "vnp_OrderType": "billpayment",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url,
        "vnp_IpAddr": client_ip or "127.0.0.1",
        "vnp_CreateDate": _format_vnpay_datetime(now),
        "vnp_ExpireDate": _format_vnpay_datetime(now + timedelta(minutes=15)),
    }

    params["vnp_SecureHash"] = _vnpay_sign(params, secret_key)

    return f"{vnpay_url}?{urlencode(sorted(params.items()), quote_via=quote_plus)}"


def _get_order_for_student(
    db: Session,
    order_id: str,
    user_id: str,
) -> Order | None:
    return (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )


def _render_checkout_error(
    request: Request,
    db: Session,
    user_id: str,
    coupon_code: str = "",
    pay_method: str = "wallet",
    error: str = "Thanh toán thất bại.",
    status_code: int = 400,
):
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
            "error": error,
            "active_page": "cart",
        },
        status_code=status_code,
    )


# ======================================================
# ⚡ BUY NOW
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

    result = cart_service.add_to_cart(db, user_id, course_id)

    request.session["cart_count"] = cart_service.get_cart_count(db, user_id)
    request.session["cart_notice"] = result.get("message") if isinstance(result, dict) else None

    if isinstance(result, dict) and result.get("status") == "error":
        return RedirectResponse("/student/course", status_code=303)

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

    cart_notice = request.session.get("cart_notice")
    request.session["cart_notice"] = None

    return templates["student"].TemplateResponse(
        "cart/cart.html",
        {
            "request": request,
            "items": items,
            "subtotal": subtotal,
            "wallet_balance": wallet_balance,
            "cart_notice": cart_notice,
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
    wants_json = wants_json_response(request)

    if not user_id:
        if wants_json:
            return JSONResponse(
                {
                    "status": "error",
                    "message": "Bạn cần đăng nhập để thêm khóa học vào giỏ.",
                    "redirect": "/auth/login",
                    "cart_count": 0,
                },
                status_code=401,
            )

        return RedirectResponse("/auth/login", status_code=302)

    result = cart_service.add_to_cart(db, user_id, course_id)

    if not isinstance(result, dict):
        result = {
            "status": "error",
            "message": "Không thể thêm khóa học vào giỏ hàng.",
        }

    cart_count = cart_service.get_cart_count(db, user_id)

    request.session["cart_count"] = cart_count
    request.session["cart_notice"] = result.get("message")

    if wants_json:
        status_code = 200

        if result.get("status") == "error":
            status_code = 400

        return JSONResponse(
            {
                "status": result.get("status", "error"),
                "message": result.get("message", "Không thể thêm vào giỏ hàng."),
                "cart_count": cart_count,
            },
            status_code=status_code,
        )

    return RedirectResponse("/student/cart", status_code=303)


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

    result = cart_service.checkout(
        db=db,
        user_id=user_id,
        coupon_code=coupon_code,
        payment_method=pay_method,
    )

    if result.get("status") == "empty":
        request.session["cart_count"] = 0
        return RedirectResponse("/student/cart", status_code=303)

    # ✅ FIX QUAN TRỌNG:
    # VNPay tạo đơn pending_payment thì phải chuyển sang cổng VNPay,
    # không được render lại checkout như lỗi.
    if result.get("status") == "pending_payment" and result.get("payment_method") == "vnpay":
        order_id = result.get("order_id")

        if not order_id:
            return _render_checkout_error(
                request=request,
                db=db,
                user_id=user_id,
                coupon_code=coupon_code,
                pay_method=pay_method,
                error="Không tạo được đơn hàng VNPay.",
                status_code=400,
            )

        return RedirectResponse(
            f"/student/cart/vnpay-pay/{order_id}",
            status_code=303,
        )

    if result.get("status") != "success":
        return _render_checkout_error(
            request=request,
            db=db,
            user_id=user_id,
            coupon_code=coupon_code,
            pay_method=pay_method,
            error=result.get("message", "Thanh toán thất bại."),
            status_code=400,
        )

    request.session["cart_count"] = 0
    request.session["last_checkout"] = result

    return RedirectResponse("/student/cart/checkout/success", status_code=303)


# ======================================================
# 🌐 VNPay Pay Redirect
# ======================================================
@router.get("/vnpay-pay/{order_id}", name="student_cart_vnpay_pay")
async def vnpay_pay(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    order = _get_order_for_student(db, order_id, user_id)

    if not order:
        return RedirectResponse(
            "/student/cart/checkout?pay_method=vnpay&error=Không tìm thấy đơn hàng VNPay",
            status_code=303,
        )

    if order.status == "paid":
        return RedirectResponse("/student/course/enrolled", status_code=303)

    if order.status != "pending":
        return RedirectResponse(
            "/student/cart/checkout?pay_method=vnpay&error=Đơn hàng không còn ở trạng thái chờ thanh toán",
            status_code=303,
        )

    try:
        client_ip = request.client.host if request.client else "127.0.0.1"
        payment_url = _build_vnpay_payment_url(
            request=request,
            order=order,
            client_ip=client_ip,
        )

        return RedirectResponse(payment_url, status_code=303)

    except Exception as e:
        return RedirectResponse(
            f"/student/cart/checkout?pay_method=vnpay&error={quote_plus(str(e))}",
            status_code=303,
        )


# ======================================================
# ✅ VNPay Return
# ======================================================
@router.get("/vnpay-return", name="student_cart_vnpay_return")
async def vnpay_return(
    request: Request,
    db: Session = Depends(get_db),
):
    params = dict(request.query_params)

    order_id = params.get("vnp_TxnRef")
    response_code = params.get("vnp_ResponseCode")
    transaction_status = params.get("vnp_TransactionStatus")
    amount_raw = params.get("vnp_Amount") or "0"
    transaction_id = params.get("vnp_TransactionNo") or params.get("vnp_BankTranNo") or ""

    if not order_id:
        return RedirectResponse(
            "/student/cart/checkout?pay_method=vnpay&error=Thiếu mã đơn hàng VNPay",
            status_code=303,
        )

    try:
        amount = Decimal(str(amount_raw)) / Decimal("100")
    except Exception:
        amount = Decimal("0.00")

    if not _verify_vnpay_signature(params):
        cart_service.mark_order_failed(db, order_id)

        return RedirectResponse(
            "/student/cart/checkout?pay_method=vnpay&error=Chữ ký VNPay không hợp lệ",
            status_code=303,
        )

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

            return RedirectResponse(
                "/student/cart/checkout/success",
                status_code=303,
            )

        return RedirectResponse(
            f"/student/cart/checkout?pay_method=vnpay&error={quote_plus(result.get('message', 'Xác nhận thanh toán thất bại'))}",
            status_code=303,
        )

    cart_service.mark_order_failed(db, order_id)

    return RedirectResponse(
        "/student/cart/checkout?pay_method=vnpay&error=Thanh toán VNPay không thành công",
        status_code=303,
    )


# ======================================================
# 📡 VNPay IPN
# ======================================================
@router.get("/vnpay-ipn")
async def vnpay_ipn(
    request: Request,
    db: Session = Depends(get_db),
):
    params = dict(request.query_params)

    order_id = params.get("vnp_TxnRef")
    response_code = params.get("vnp_ResponseCode")
    transaction_status = params.get("vnp_TransactionStatus")
    amount_raw = params.get("vnp_Amount") or "0"
    transaction_id = params.get("vnp_TransactionNo") or params.get("vnp_BankTranNo") or ""

    if not order_id:
        return JSONResponse({"RspCode": "01", "Message": "Order not found"})

    if not _verify_vnpay_signature(params):
        return JSONResponse({"RspCode": "97", "Message": "Invalid signature"})

    try:
        amount = Decimal(str(amount_raw)) / Decimal("100")
    except Exception:
        return JSONResponse({"RspCode": "04", "Message": "Invalid amount"})

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        return JSONResponse({"RspCode": "01", "Message": "Order not found"})

    if response_code == "00" and transaction_status == "00":
        result = cart_service.confirm_paid_order(
            db=db,
            order_id=order_id,
            amount=amount,
            transaction_id=transaction_id,
            payment_method="vnpay",
        )

        if result.get("status") == "success":
            return JSONResponse({"RspCode": "00", "Message": "Confirm Success"})

        if result.get("code") == "04":
            return JSONResponse({"RspCode": "04", "Message": "Invalid amount"})

        return JSONResponse({"RspCode": "99", "Message": result.get("message", "Unknown error")})

    cart_service.mark_order_failed(db, order_id)
    return JSONResponse({"RspCode": "00", "Message": "Payment failed confirmed"})


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
        return RedirectResponse("/student/course/enrolled", status_code=303)

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