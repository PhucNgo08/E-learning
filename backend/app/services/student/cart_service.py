"""
=====================================================
🛒 Service: Shopping Cart for Students (PREMIUM FIX 2025)
- Ví điện tử tích hợp
- Checkout an toàn với Decimal
- Không dùng attribute final_price runtime (FIXED)
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

# Ví điện tử
from app.services.wallet_service import (
    get_balance,
    student_pay
)

# =====================================================
# Helper Decimal
# =====================================================
def D(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# =====================================================
# 0) Giá sau giảm giá (%)
# =====================================================
def get_final_price(course: Course) -> Decimal:
    price = D(course.price or 0)
    discount = D(course.discount_percent or 0)

    if discount > 0:
        final_price = price * (Decimal("100") - discount) / Decimal("100")
    else:
        final_price = price

    return final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =====================================================
# 1) Kiểm tra user đã mua khóa học
# =====================================================
def is_purchased(db: Session, user_id: str, course_id: str) -> bool:
    return db.query(UserCourse).filter(
        UserCourse.user_id == user_id,
        UserCourse.course_id == course_id
    ).first() is not None


# =====================================================
# 2) Lấy giỏ hàng
# =====================================================
def get_cart(db: Session, user_id: str):
    items = (
        db.query(CartItem)
        .join(Course, CartItem.course_id == Course.id)
        .filter(CartItem.user_id == user_id)
        .all()
    )

    # Gắn final_price runtime để hiển thị UI
    for item in items:
        if item.course:
            item.course.final_price = get_final_price(item.course)

    return items


def get_cart_count(db: Session, user_id: str) -> int:
    return db.query(CartItem).filter(CartItem.user_id == user_id).count()


def get_cart_total(db: Session, user_id: str) -> Decimal:
    items = get_cart(db, user_id)
    if not items:
        return Decimal("0")
    return sum((get_final_price(item.course) for item in items), Decimal("0"))


# =====================================================
# 3) Coupon
# =====================================================
def apply_coupon(total: Decimal, coupon_code: str) -> Decimal:
    if not coupon_code:
        return total

    mapping = {
        "GIAM50": Decimal("0.5"),
        "GIAM20": Decimal("0.2"),
        "GIAM10": Decimal("0.1"),
    }

    rate = mapping.get(coupon_code.upper().strip())
    if not rate:
        return total

    discounted = total * (Decimal("1") - rate)
    return discounted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =====================================================
# 4) Payment fee
# =====================================================
def get_payment_fee(amount: Decimal, method: str) -> Decimal:
    if method == "vnpay":
        return (amount * Decimal("0.02")).quantize(Decimal("0.01"))
    if method == "card":
        return (amount * Decimal("0.03")).quantize(Decimal("0.01"))
    return Decimal("0")


# =====================================================
# 5) Add to cart
# =====================================================
def add_to_cart(db: Session, user_id: str, course_id: str):

    if is_purchased(db, user_id, course_id):
        return None

    # Đã ghi danh → không thêm giỏ
    enrolled = db.query(Enrollment).filter(
        Enrollment.user_id == user_id,
        Enrollment.course_id == course_id,
        Enrollment.enrollment_status.in_(["approved", "active", "applied"]),
    ).first()

    if enrolled:
        return None

    exists = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.course_id == course_id
    ).first()

    if exists:
        return exists

    item = CartItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# =====================================================
# 6) Remove one item
# =====================================================
def remove_from_cart(db: Session, user_id: str, item_id: str) -> bool:
    cart = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == user_id
    ).first()

    if not cart:
        return False

    db.delete(cart)
    db.commit()
    return True


# =====================================================
# 7) CHECKOUT (Wallet-integrated, Decimal-safe)
# =====================================================
def checkout(db: Session, user_id: str, coupon_code=None, payment_method="wallet"):

    cart_items = get_cart(db, user_id)
    if not cart_items:
        return {"status": "empty", "message": "Giỏ hàng trống."}

    # 1. Tính tiền
    subtotal = get_cart_total(db, user_id)
    discounted = apply_coupon(subtotal, coupon_code)
    fee = get_payment_fee(discounted, payment_method)
    total_paid = discounted + fee

    # 2. Kiểm tra số dư ví
    balance = D(get_balance(db, user_id))

    if balance < total_paid:
        raise Exception("❌ Số dư ví không đủ! Vui lòng nạp thêm tiền.")

    # 3. Trừ tiền ví
    student_pay(
        db=db,
        user_id=user_id,
        amount=float(total_paid),
        description=f"Thanh toán khóa học: {', '.join(i.course.course_name for i in cart_items)}"
    )

    # 4. Tạo Order
    transaction_id = str(uuid.uuid4())

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

    purchased_list = []

    # 5. Tạo OrderItem + Enrollment + Purchased
    for item in cart_items:
        course = item.course
        cid = item.course_id

        final_price = get_final_price(course)

        db.add(OrderItem(
            id=str(uuid.uuid4()),
            order_id=order.id,
            course_id=cid,
            price=final_price,
        ))

        # Enrollment
        enrolled = db.query(Enrollment).filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == cid
        ).first()

        if not enrolled:
            db.add(Enrollment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=cid,
                enrollment_status="approved",
                applied_at=datetime.utcnow(),
            ))

        # Purchased
        purchased = db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.course_id == cid
        ).first()

        if not purchased:
            db.add(UserCourse(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=cid,
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
        "purchased_courses": purchased_list,
        "payment_method": payment_method,
    }


# =====================================================
# 8) Clear cart
# =====================================================
def clear_cart(db: Session, user_id: str):
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()
