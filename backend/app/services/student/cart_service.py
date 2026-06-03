
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session, joinedload

from app.models.user_course import UserCourse
from app.models.cart_item import CartItem
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.common.course_access_service import has_course_access
from app.services.wallet_service import get_balance, student_pay


TWOPLACES = Decimal("0.01")

SUPPORTED_PAYMENT_METHODS = {"wallet", "vnpay"}

COUPON_MAPPING = {
    "GIAM50": Decimal("0.50"),
    "GIAM20": Decimal("0.20"),
    "GIAM10": Decimal("0.10"),
}

VALID_ENROLLMENT_MODES = {"auto", "approval", "invite_only"}

PAYMENT_LABELS = {
    "wallet": "Ví nội bộ",
    "vnpay": "VNPay Sandbox",
}

ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}

BLOCK_CART_ENROLLMENT_STATUSES = {
    "approved",
    "active",
    "applied",
    "completed",
}


# ======================================================
# MONEY HELPERS
# ======================================================
def D(value) -> Decimal:
    if value is None:
        return Decimal("0.00")

    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def as_vnd_number(value) -> float:
    return float(D(value))


def get_final_price(course: Course) -> Decimal:
    price = D(getattr(course, "price", 0) or 0)
    discount = D(getattr(course, "discount_percent", 0) or 0)

    if discount > 0:
        price = price * (Decimal("100") - discount) / Decimal("100")

    return price.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def get_payment_label(method: str) -> str:
    return PAYMENT_LABELS.get((method or "").strip().lower(), "Thanh toán")


# ======================================================
# ACCESS / ENROLLMENT HELPERS
# ======================================================
def is_purchased(db: Session, user_id: str, course_id: str) -> bool:
    """
    Giữ nguyên tên hàm để tránh vỡ import cũ.
    Ý nghĩa: user đã có quyền học khóa hay chưa.
    """
    return has_course_access(db, user_id, course_id)


def _get_existing_enrollment(
    db: Session,
    user_id: str,
    course_id: str,
):
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
        )
        .first()
    )


# ======================================================
# CART
# ======================================================
def get_cart(db: Session, user_id: str):
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.course))
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.added_at.desc())
        .all()
    )

    clean_items = []

    for item in items:
        if not item.course:
            continue

        item.course.final_price = get_final_price(item.course)
        clean_items.append(item)

    return clean_items


def get_cart_count(db: Session, user_id: str) -> int:
    return (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .count()
    )


def get_cart_total(db: Session, user_id: str) -> Decimal:
    items = get_cart(db, user_id)

    if not items:
        return Decimal("0.00")

    return sum(
        (D(item.course.final_price) for item in items),
        Decimal("0.00"),
    ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def add_to_cart(
    db: Session,
    user_id: str,
    course_id: str,
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id)
        .first()
    )

    if not course:
        return {
            "status": "error",
            "message": "Không tìm thấy khóa học.",
        }

    enrollment_mode = (
        getattr(course, "enrollment_mode", "auto") or "auto"
    ).strip().lower()

    if enrollment_mode == "invite_only":
        return {
            "status": "error",
            "message": "Khóa học này chỉ ghi danh theo lời mời của quản trị viên/giảng viên.",
        }

    if enrollment_mode not in VALID_ENROLLMENT_MODES:
        return {
            "status": "error",
            "message": "Chế độ ghi danh của khóa học không hợp lệ.",
        }

    if has_course_access(db, user_id, course_id):
        return {
            "status": "exists",
            "message": "Bạn đã sở hữu hoặc đã được ghi danh khóa học này.",
        }

    enrolled = _get_existing_enrollment(db, user_id, course_id)

    if enrolled and (enrolled.enrollment_status or "").strip().lower() in BLOCK_CART_ENROLLMENT_STATUSES:
        return {
            "status": "exists",
            "message": "Khóa học đã có trong danh sách học của bạn.",
        }

    exists = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.course_id == course_id,
        )
        .first()
    )

    if exists:
        return {
            "status": "exists",
            "message": "Khóa học đã có trong giỏ hàng.",
            "item": exists,
        }

    item = CartItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "status": "success",
        "message": "Đã thêm vào giỏ hàng.",
        "item": item,
    }


def remove_from_cart(
    db: Session,
    user_id: str,
    item_id: str,
) -> bool:
    cart = (
        db.query(CartItem)
        .filter(
            CartItem.id == item_id,
            CartItem.user_id == user_id,
        )
        .first()
    )

    if not cart:
        return False

    db.delete(cart)
    db.commit()

    return True


def clear_cart(db: Session, user_id: str):
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()


# ======================================================
# COUPON / CHECKOUT SUMMARY
# ======================================================
def apply_coupon(
    total: Decimal,
    coupon_code: str | None,
):
    total = D(total)
    code = (coupon_code or "").strip().upper()

    if not code:
        return total, None, Decimal("0.00")

    rate = COUPON_MAPPING.get(code)

    if rate is None:
        return total, None, Decimal("0.00")

    discounted = (total * (Decimal("1") - rate)).quantize(
        TWOPLACES,
        rounding=ROUND_HALF_UP,
    )

    discount_amount = (total - discounted).quantize(
        TWOPLACES,
        rounding=ROUND_HALF_UP,
    )

    return discounted, code, discount_amount


def get_payment_fee(
    amount: Decimal,
    method: str,
) -> Decimal:
    """
    Bỏ phụ phí VNPay để demo dễ hiểu.
    """
    return Decimal("0.00")


def build_checkout_summary(
    db: Session,
    user_id: str,
    coupon_code: str | None = None,
    payment_method: str = "wallet",
):
    payment_method = (payment_method or "wallet").strip().lower()

    if payment_method not in SUPPORTED_PAYMENT_METHODS:
        payment_method = "wallet"

    items = get_cart(db, user_id)

    subtotal = sum(
        (D(item.course.final_price) for item in items),
        Decimal("0.00"),
    ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    discounted, valid_coupon, discount_amount = apply_coupon(
        subtotal,
        coupon_code,
    )

    fee = get_payment_fee(discounted, payment_method)

    total_paid = (discounted + fee).quantize(
        TWOPLACES,
        rounding=ROUND_HALF_UP,
    )

    return {
        "items": items,
        "subtotal": subtotal,
        "discounted": discounted,
        "discount_amount": discount_amount,
        "fee": fee,
        "total_paid": total_paid,
        "coupon_code": valid_coupon or (coupon_code or "").strip().upper() or "",
        "valid_coupon": valid_coupon,
        "payment_method": payment_method,
        "payment_label": get_payment_label(payment_method),
        "wallet_balance": D(get_balance(db, user_id)),
    }


# ======================================================
# GRANT COURSE ACCESS
# ======================================================
def _prepare_enrollment_data(
    course: Course,
    now: datetime,
):
    """
    Khi sinh viên đã thanh toán khóa học bằng ví nội bộ hoặc VNPay thành công
    thì phải cấp quyền học ngay.

    Không để enrollment_status = 'applied' nữa,
    vì 'applied' chỉ phù hợp khi sinh viên xin đăng ký chờ duyệt,
    không phù hợp với nghiệp vụ đã thanh toán.
    """
    enrollment_mode = (
        getattr(course, "enrollment_mode", "auto") or "auto"
    ).strip().lower()

    if enrollment_mode == "invite_only":
        raise ValueError(
            "Khóa học này chỉ ghi danh theo lời mời của quản trị viên/giảng viên."
        )

    return {
        "enrollment_status": "active",
        "approved_at": now,
        "enrolled_at": now,
    }


def _upsert_user_course(
    db: Session,
    user_id: str,
    course_id: str,
    order_id: str | None,
    now: datetime,
    access_status: str = "active",
):
    user_course = (
        db.query(UserCourse)
        .filter(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id,
        )
        .first()
    )

    if not user_course:
        db.add(
            UserCourse(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                order_id=order_id,
                purchased_at=now,
                access_status=access_status,
            )
        )
        return

    if order_id and not getattr(user_course, "order_id", None):
        user_course.order_id = order_id

    if not getattr(user_course, "purchased_at", None):
        user_course.purchased_at = now

    user_course.access_status = access_status


def _grant_course_access(
    db: Session,
    user_id: str,
    course: Course,
    now: datetime,
    order_id: str | None = None,
):
    enrollment_data = _prepare_enrollment_data(course, now)
    target_status = enrollment_data["enrollment_status"]

    enrolled = _get_existing_enrollment(db, user_id, course.id)

    if not enrolled:
        db.add(
            CourseEnrollment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course.id,
                enrollment_status=target_status,
                enrollment_source="purchase",
                applied_at=now,
                approved_at=enrollment_data["approved_at"],
                enrolled_at=enrollment_data["enrolled_at"],
            )
        )

        if (
            target_status in ACTIVE_ENROLLMENT_STATUSES
            and hasattr(course, "current_students")
            and course.current_students is not None
        ):
            course.current_students = int(course.current_students or 0) + 1

    else:
        old_status = (enrolled.enrollment_status or "").strip().lower()

        enrolled.enrollment_status = "active"
        enrolled.enrollment_source = "purchase"

        if not getattr(enrolled, "applied_at", None):
            enrolled.applied_at = now

        enrolled.approved_at = now
        enrolled.enrolled_at = now

        if (
            old_status not in ACTIVE_ENROLLMENT_STATUSES
            and hasattr(course, "current_students")
            and course.current_students is not None
        ):
            course.current_students = int(course.current_students or 0) + 1

    _upsert_user_course(
        db=db,
        user_id=user_id,
        course_id=course.id,
        order_id=order_id,
        now=now,
        access_status="active",
    )


# ======================================================
# CHECKOUT
# ======================================================
def checkout(
    db: Session,
    user_id: str,
    coupon_code: str | None = None,
    payment_method: str = "wallet",
):
    payment_method = (payment_method or "wallet").strip().lower()

    if payment_method not in SUPPORTED_PAYMENT_METHODS:
        return {
            "status": "error",
            "message": "Phương thức thanh toán không hợp lệ.",
        }

    summary = build_checkout_summary(
        db=db,
        user_id=user_id,
        coupon_code=coupon_code,
        payment_method=payment_method,
    )

    cart_items = summary["items"]

    if not cart_items:
        return {
            "status": "empty",
            "message": "Giỏ hàng trống.",
        }

    subtotal = D(summary["subtotal"])
    discounted = D(summary["discounted"])
    discount_amount = D(summary["discount_amount"])
    fee = D(summary["fee"])
    total_paid = D(summary["total_paid"])
    valid_coupon = summary["valid_coupon"]
    wallet_balance_before = D(summary["wallet_balance"])

    if payment_method == "wallet" and wallet_balance_before < total_paid:
        return {
            "status": "error",
            "message": "Số dư ví không đủ để thanh toán đơn hàng này.",
            **summary,
        }

    try:
        now = datetime.utcnow()

        if payment_method == "vnpay":
            db.query(Order).filter(
                Order.user_id == user_id,
                Order.payment_method == "vnpay",
                Order.status == "pending",
            ).update(
                {
                    "status": "failed",
                    "cancelled_at": now,
                },
                synchronize_session=False,
            )
            db.flush()

        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            total_amount=total_paid,
            status="pending",
            payment_method=payment_method,
            paid_at=None,
        )

        db.add(order)
        db.flush()

        valid_cart_items = []

        for item in cart_items:
            course = item.course

            if not course:
                continue

            enrollment_mode = (
                getattr(course, "enrollment_mode", "auto") or "auto"
            ).strip().lower()

            if enrollment_mode == "invite_only":
                db.delete(item)
                continue

            if has_course_access(db, user_id, course.id):
                db.delete(item)
                continue

            course_price = D(getattr(course, "price", 0) or 0)
            final_course_price = get_final_price(course)
            course_discount_percent = int(
                getattr(course, "discount_percent", 0) or 0
            )

            db.add(
                OrderItem(
                    id=str(uuid.uuid4()),
                    order_id=order.id,
                    course_id=item.course_id,
                    price=course_price,
                    discount_percent=course_discount_percent,
                    final_price=final_course_price,
                )
            )

            valid_cart_items.append(item)

        if not valid_cart_items:
            db.rollback()
            return {
                "status": "error",
                "message": "Không có khóa học hợp lệ trong giỏ hàng.",
            }

        if payment_method == "wallet":
            tx = student_pay(
                db=db,
                user_id=user_id,
                amount=float(total_paid),
                description=f"Thanh toán đơn hàng {order.id}",
                order_id=order.id,
                auto_commit=False,
            )

            order.status = "paid"
            order.paid_at = now

            purchased_list: list[str] = []

            for item in valid_cart_items:
                course = item.course
                _grant_course_access(db, user_id, course, now, order.id)
                purchased_list.append(course.course_name)
                db.delete(item)

            db.commit()
            db.refresh(order)

            wallet_after = D(tx.balance_after)

            return {
                "status": "success",
                "order_id": order.id,
                "transaction_id": tx.id,
                "subtotal": as_vnd_number(subtotal),
                "discounted": as_vnd_number(discounted),
                "discount_amount": as_vnd_number(discount_amount),
                "fee": as_vnd_number(fee),
                "total_paid": as_vnd_number(total_paid),
                "coupon_code": valid_coupon or "",
                "payment_method": payment_method,
                "payment_label": get_payment_label(payment_method),
                "wallet_before": as_vnd_number(wallet_balance_before),
                "wallet_after": as_vnd_number(wallet_after),
                "wallet_delta": as_vnd_number(total_paid),
                "purchased_courses": purchased_list,
                "demo_gateway": False,
            }

        db.commit()
        db.refresh(order)

        return {
            "status": "pending_payment",
            "order_id": order.id,
            "transaction_id": None,
            "subtotal": as_vnd_number(subtotal),
            "discounted": as_vnd_number(discounted),
            "discount_amount": as_vnd_number(discount_amount),
            "fee": as_vnd_number(fee),
            "total_paid": as_vnd_number(total_paid),
            "coupon_code": valid_coupon or "",
            "payment_method": payment_method,
            "payment_label": get_payment_label(payment_method),
            "wallet_before": as_vnd_number(wallet_balance_before),
            "wallet_after": as_vnd_number(wallet_balance_before),
            "wallet_delta": 0.0,
            "purchased_courses": [],
            "demo_gateway": False,
            "message": "Đơn hàng đã được tạo và đang chờ thanh toán VNPay.",
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e),
            **summary,
        }


# ======================================================
# VNPay CONFIRM / SUCCESS RESULT
# ======================================================
def _get_order_original_subtotal(order: Order) -> Decimal:
    """
    Tính tổng ban đầu của đơn từ order_items.

    order.total_amount là số tiền đã thanh toán sau khi áp mã giảm giá.
    order_items.final_price là giá khóa học trước khi áp mã giảm giá toàn đơn.
    Vì vậy khi VNPay return về, dùng hàm này để hiển thị lại:
    - Tổng ban đầu
    - Giảm giá
    - Sau giảm giá
    - Tổng thanh toán
    """
    total = Decimal("0.00")

    for item in order.items or []:
        item_amount = getattr(item, "final_price", None)

        if item_amount is None:
            item_amount = getattr(item, "price", 0) or 0

        total += D(item_amount)

    return total.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _build_paid_order_result(
    order: Order,
    transaction_id: str | None,
    payment_method: str,
    purchased_list: list[str],
    message: str = "Thanh toán thành công, khóa học đã được kích hoạt.",
):
    """
    Chuẩn hóa dữ liệu trả về cho payment_success.html.

    Fix lỗi VNPay hiện Giảm giá = 0đ:
    - subtotal lấy từ order_items
    - total_paid lấy từ orders.total_amount
    - discount_amount = subtotal - total_paid
    """
    subtotal = _get_order_original_subtotal(order)
    total_paid = D(order.total_amount)

    if subtotal <= 0:
        subtotal = total_paid

    discount_amount = (subtotal - total_paid).quantize(
        TWOPLACES,
        rounding=ROUND_HALF_UP,
    )

    if discount_amount < 0:
        discount_amount = Decimal("0.00")

    return {
        "status": "success",
        "code": "00",
        "message": message,
        "order_id": order.id,
        "transaction_id": transaction_id or "",
        "subtotal": as_vnd_number(subtotal),
        "discounted": as_vnd_number(total_paid),
        "discount_amount": as_vnd_number(discount_amount),
        "fee": 0,
        "total_paid": as_vnd_number(total_paid),
        "coupon_code": "",
        "payment_method": payment_method,
        "payment_label": get_payment_label(payment_method),
        "wallet_before": 0,
        "wallet_after": 0,
        "wallet_delta": 0,
        "purchased_courses": purchased_list,
        "demo_gateway": False,
    }


def confirm_paid_order(
    db: Session,
    order_id: str,
    amount: Decimal,
    transaction_id: str | None = None,
    payment_method: str = "vnpay",
):
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.course))
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        return {
            "status": "error",
            "code": "01",
            "message": "Không tìm thấy đơn hàng.",
        }

    order_amount = D(order.total_amount)
    paid_amount = D(amount)

    if order_amount != paid_amount:
        return {
            "status": "error",
            "code": "04",
            "message": "Số tiền thanh toán không khớp.",
        }

    purchased_list = [
        item.course.course_name
        for item in order.items
        if item.course
    ]

    if order.status == "paid":
        return _build_paid_order_result(
            order=order,
            transaction_id=transaction_id,
            payment_method=payment_method,
            purchased_list=purchased_list,
            message="Đơn hàng đã được xác nhận trước đó.",
        )

    if order.status != "pending":
        return {
            "status": "error",
            "code": "02",
            "message": "Trạng thái đơn hàng không hợp lệ.",
        }

    try:
        now = datetime.utcnow()

        order.status = "paid"
        order.paid_at = now
        order.payment_method = payment_method

        for item in order.items:
            course = item.course

            if not course:
                continue

            _grant_course_access(
                db=db,
                user_id=order.user_id,
                course=course,
                now=now,
                order_id=order.id,
            )

            cart_item = (
                db.query(CartItem)
                .filter(
                    CartItem.user_id == order.user_id,
                    CartItem.course_id == course.id,
                )
                .first()
            )

            if cart_item:
                db.delete(cart_item)

        db.commit()
        db.refresh(order)

        return _build_paid_order_result(
            order=order,
            transaction_id=transaction_id,
            payment_method=payment_method,
            purchased_list=purchased_list,
        )

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "code": "99",
            "message": str(e),
        }


def mark_order_failed(
    db: Session,
    order_id: str | None,
):
    if not order_id:
        return None

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if order and order.status == "pending":
        order.status = "failed"
        order.cancelled_at = datetime.utcnow()
        db.commit()

    return order
