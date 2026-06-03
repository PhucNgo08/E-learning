from __future__ import annotations

from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session


PAID_STATUSES = ("paid", "completed", "success")
TOPUP_SUCCESS_STATUSES = ("approved", "completed", "paid", "success", "confirmed")


def _money(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _format_vnd(value) -> str:
    return f"{int(round(_money(value))):,}".replace(",", ".") + "đ"


def get_revenue_summary(db: Session) -> dict:
    """
    Doanh thu chuẩn lấy từ orders đã thanh toán.
    Không cộng wallet_transactions để tránh đếm trùng với orders.
    """
    total_row = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_revenue,
                COUNT(*) AS total_orders
            FROM orders
            WHERE LOWER(status) IN ('paid', 'completed', 'success')
            """
        )
    ).mappings().first()

    method_rows = db.execute(
        text(
            """
            SELECT
                CASE
                    WHEN LOWER(COALESCE(payment_method, '')) IN ('wallet', 'internal_wallet', 'vi_noi_bo')
                        THEN 'wallet'
                    WHEN LOWER(COALESCE(payment_method, '')) IN ('vnpay', 'vn_pay', 'vnpay_qr', 'vnpay_atm')
                        THEN 'vnpay'
                    ELSE COALESCE(NULLIF(LOWER(payment_method), ''), 'other')
                END AS method_key,
                COUNT(*) AS order_count,
                COALESCE(SUM(total_amount), 0) AS amount
            FROM orders
            WHERE LOWER(status) IN ('paid', 'completed', 'success')
            GROUP BY method_key
            ORDER BY amount DESC
            """
        )
    ).mappings().all()

    today_row = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS today_revenue,
                COUNT(*) AS today_orders
            FROM orders
            WHERE LOWER(status) IN ('paid', 'completed', 'success')
              AND DATE(COALESCE(paid_at, created_at)) = CURDATE()
            """
        )
    ).mappings().first()

    month_row = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS month_revenue,
                COUNT(*) AS month_orders
            FROM orders
            WHERE LOWER(status) IN ('paid', 'completed', 'success')
              AND YEAR(COALESCE(paid_at, created_at)) = YEAR(CURDATE())
              AND MONTH(COALESCE(paid_at, created_at)) = MONTH(CURDATE())
            """
        )
    ).mappings().first()

    topup_row = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS topup_amount,
                COUNT(*) AS topup_count
            FROM wallet_topup_requests
            WHERE LOWER(status) IN ('approved', 'completed', 'paid', 'success', 'confirmed')
            """
        )
    ).mappings().first()

    wallet_revenue = 0.0
    vnpay_revenue = 0.0
    other_revenue = 0.0

    method_stats = []
    for row in method_rows:
        method_key = row["method_key"]
        amount = _money(row["amount"])

        if method_key == "wallet":
            label = "Ví nội bộ"
            wallet_revenue += amount
        elif method_key == "vnpay":
            label = "VNPay"
            vnpay_revenue += amount
        else:
            label = "Khác"
            other_revenue += amount

        method_stats.append(
            {
                "method_key": method_key,
                "label": label,
                "order_count": row["order_count"],
                "amount": amount,
                "amount_text": _format_vnd(amount),
            }
        )

    total_revenue = _money(total_row["total_revenue"] if total_row else 0)

    return {
        "total_revenue": total_revenue,
        "total_revenue_text": _format_vnd(total_revenue),
        "total_orders": total_row["total_orders"] if total_row else 0,

        "wallet_revenue": wallet_revenue,
        "wallet_revenue_text": _format_vnd(wallet_revenue),

        "vnpay_revenue": vnpay_revenue,
        "vnpay_revenue_text": _format_vnd(vnpay_revenue),

        "other_revenue": other_revenue,
        "other_revenue_text": _format_vnd(other_revenue),

        "today_revenue": _money(today_row["today_revenue"] if today_row else 0),
        "today_revenue_text": _format_vnd(today_row["today_revenue"] if today_row else 0),
        "today_orders": today_row["today_orders"] if today_row else 0,

        "month_revenue": _money(month_row["month_revenue"] if month_row else 0),
        "month_revenue_text": _format_vnd(month_row["month_revenue"] if month_row else 0),
        "month_orders": month_row["month_orders"] if month_row else 0,

        "topup_amount": _money(topup_row["topup_amount"] if topup_row else 0),
        "topup_amount_text": _format_vnd(topup_row["topup_amount"] if topup_row else 0),
        "topup_count": topup_row["topup_count"] if topup_row else 0,

        "method_stats": method_stats,
    }


def get_recent_paid_orders(db: Session, limit: int = 20) -> list[dict]:
    limit = max(1, min(limit or 20, 100))

    rows = db.execute(
        text(
            """
            SELECT
                o.id,
                o.total_amount,
                o.status,
                o.payment_method,
                o.created_at,
                o.paid_at,
                u.username,
                up.full_name
            FROM orders o
            JOIN users u ON u.id = o.user_id
            LEFT JOIN user_profiles up ON up.user_id = u.id
            WHERE LOWER(o.status) IN ('paid', 'completed', 'success')
            ORDER BY COALESCE(o.paid_at, o.created_at) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()

    data = []
    for row in rows:
        method = (row["payment_method"] or "other").lower()
        if method in ("wallet", "internal_wallet", "vi_noi_bo"):
            method_label = "Ví nội bộ"
        elif method in ("vnpay", "vn_pay", "vnpay_qr", "vnpay_atm"):
            method_label = "VNPay"
        else:
            method_label = method.upper()

        data.append(
            {
                "id": row["id"],
                "username": row["username"],
                "full_name": row["full_name"] or row["username"],
                "total_amount": _money(row["total_amount"]),
                "total_amount_text": _format_vnd(row["total_amount"]),
                "status": row["status"],
                "payment_method": method,
                "payment_method_label": method_label,
                "created_at": row["created_at"],
                "paid_at": row["paid_at"],
            }
        )

    return data