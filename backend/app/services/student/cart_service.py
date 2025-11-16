"""
=====================================================
🛒 Service: Shopping Cart for Students (FINAL PREMIUM 2025)
- subtotal
- discounted
- fee
- total_paid
- FULL Decimal-safe
=====================================================
"""

import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session

from app.models.cart_item import CartItem
from app.models.course import Course
from app.models.user_course import UserCourse
from app.models.enrollment import Enrollment
from app.models.order import Order
from app.models.order_item import OrderItem


# =====================================================
# 🔥 Helper: Convert to Decimal safely
# =====================================================
def D(val) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# =====================================================
# 🔥 0) Tính giá sau giảm giá (%)
# =====================================================
def get_final_price(course: Course) -> Decimal:
    try:
        price = D(course.price or 0)
        discount = D(course.discount_percent or 0)

        if discount > 0:
            final_price = price * (Decimal("100") - discount) / Decimal("100")
        else:
            final_price = price

        return final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    except:
        return D(course.price or 0)


# =====================================================
# 🔥 1) Kiểm tra user đã mua khóa học chưa
# =====================================================
def is_purchased(db: Session, user_id: str, course_id: str) -> bool:
    return (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
        .first()
        is not None
    )


# =====================================================
# 2) Lấy giỏ hàng + gắn final_price
# =====================================================
def get_cart(db: Session, user_id: str):
    items = (
        db.query(CartItem)
        .join(Course, CartItem.course_id == Course.id)
        .filter(CartItem.user_id == user_id)
        .all()
    )

    for item in items:
        if item.course:
            item.course.final_price = get_final_price(item.course)

    return items


# =====================================================
# 2.1) Đếm giỏ hàng
# =====================================================
def get_cart_count(db: Session, user_id: str) -> int:
    return db.query(CartItem).filter(CartItem.user_id == user_id).count()


# =====================================================
# 2.2) Tổng tiền (Decimal-safe)
# =====================================================
def get_cart_total(db: Session, user_id: str) -> Decimal:
    items = get_cart(db, user_id)
    if not items:
        return Decimal("0")
    return sum((item.course.final_price for item in items), Decimal("0"))


# =====================================================
# 2.3) Áp dụng coupon (Decimal)
# =====================================================
def apply_coupon(total: Decimal, coupon_code: str) -> Decimal:
    if not coupon_code:
        return total

    code = coupon_code.upper().strip()

    mapping = {
        "GIAM50": Decimal("0.5"),
        "GIAM20": Decimal("0.2"),
        "GIAM10": Decimal("0.1"),
    }

    rate = mapping.get(code)
    if not rate:
        return total

    discounted = total * (Decimal("1") - rate)
    return discounted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =====================================================
# 2.4) Payment fee (Decimal)
# =====================================================
def get_payment_fee(amount: Decimal, method: str) -> Decimal:
    if method == "vnpay":
        return (amount * Decimal("0.02")).quantize(Decimal("0.01"))
    if method == "card":
        return (amount * Decimal("0.03")).quantize(Decimal("0.01"))
    return Decimal("0")


# =====================================================
# 3) Add to cart
# =====================================================
def add_to_cart(db: Session, user_id: str, course_id: str):

    if is_purchased(db, user_id, course_id):
        return None

    enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
            Enrollment.enrollment_status.in_(["approved", "active", "applied"]),
        )
        .first()
    )
    if enrolled:
        return None

    exists = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.course_id == course_id)
        .first()
    )
    if exists:
        return exists

    item = CartItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id,
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# =====================================================
# 4) Remove item
# =====================================================
def remove_from_cart(db: Session, user_id: str, item_id: str) -> bool:
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == user_id)
        .first()
    )
    if not item:
        return False

    db.delete(item)
    db.commit()
    return True


# =====================================================
# 5) CHECKOUT FINAL (Decimal-safe)
# =====================================================
def checkout(
    db: Session,
    user_id: str,
    coupon_code: str = None,
    payment_method: str = "momo"
):
    cart_items = get_cart(db, user_id)

    if not cart_items:
        return {"status": "empty", "message": "Giỏ hàng trống."}

    # -----------------------------
    # 1. Tính tiền
    # -----------------------------
    subtotal = get_cart_total(db, user_id)
    discounted = apply_coupon(subtotal, coupon_code)
    fee = get_payment_fee(discounted, payment_method)
    total_paid = discounted + fee

    # -----------------------------
    # 2. Transaction ID
    # -----------------------------
    transaction_id = str(uuid.uuid4())

    # -----------------------------
    # 3. Tạo ORDER
    # -----------------------------
    order = Order(
        id=str(uuid.uuid4()),
        user_id=user_id,
        total_amount=total_paid,
        status="paid",
        payment_method=payment_method,
        paid_at=datetime.utcnow(),
    )
    db.add(order)
    db.flush()

    # -----------------------------
    # 4. Enrollment + Purchased + OrderItems
    # -----------------------------
    purchased_list = []

    for item in cart_items:
        course = item.course
        course_id = item.course_id

        db.add(OrderItem(
            id=str(uuid.uuid4()),
            order_id=order.id,
            course_id=course_id,
            price=course.final_price,
        ))

        exists = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        if not exists:
            db.add(Enrollment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                enrollment_status="approved",
                applied_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            ))

        purchased = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
            .first()
        )

        if not purchased:
            db.add(UserCourse(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                purchased_at=datetime.utcnow(),
            ))

        purchased_list.append(course.course_name)
        db.delete(item)

    db.commit()

    return {
        "status": "success",
        "transaction_id": transaction_id,
        "order_id": order.id,
        "subtotal": float(subtotal),
        "discounted": float(discounted),
        "fee": float(fee),
        "total_paid": float(total_paid),
        "payment_method": payment_method,
        "coupon": coupon_code,
        "purchased_courses": purchased_list,
    }
