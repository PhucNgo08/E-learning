# app/utils/db_error_helper.py
import logging
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import DataError, IntegrityError

logger = logging.getLogger(__name__)


def get_decimal_max_from_column(model, col_name: str, fallback: Decimal) -> Decimal:
    """
    Tự tính max dựa trên DECIMAL(precision, scale).
    Ví dụ DECIMAL(10,2) => 99,999,999.99
    """
    try:
        col = model.__table__.columns.get(col_name)
        t = getattr(col, "type", None)
        precision = getattr(t, "precision", None)
        scale = getattr(t, "scale", None)
        if precision and scale is not None:
            int_digits = precision - scale
            return (Decimal(10) ** int_digits) - (Decimal(1) / (Decimal(10) ** scale))
    except Exception:
        pass
    return fallback


def parse_money_vn(raw: str) -> Decimal:
    """
    Hỗ trợ input kiểu:
    - 10000.00
    - 10000,00
    - 10.000,00
    - 10 000,00
    """
    v = (raw or "").strip()
    if v == "":
        return Decimal("0")

    v = v.replace(" ", "")

    # 10.000,00 -> 10000.00
    if "," in v and "." in v and v.rfind(",") > v.rfind("."):
        v = v.replace(".", "").replace(",", ".")
    # 10000,00 -> 10000.00
    elif "," in v and "." not in v:
        v = v.replace(",", ".")

    return Decimal(v)


def humanize_db_error(e: Exception, *, price_max: Decimal | None = None) -> str:
    """
    Dịch lỗi DB sang thông báo dễ hiểu (không lộ SQL).
    """
    orig = getattr(e, "orig", None)
    code = None
    msg = str(e)

    # pymysql thường có orig.args = (code, message)
    if orig is not None and hasattr(orig, "args") and len(orig.args) >= 2:
        code = orig.args[0]
        msg = orig.args[1]

    msg_l = (msg or "").lower()

    # 1264 Out of range
    if code == 1264 or "out of range value" in msg_l:
        if "price" in msg_l and price_max is not None:
            return f"Giá khóa học vượt quá giới hạn cho phép. Tối đa: {price_max:,.2f} VNĐ."
        return "Giá trị nhập vượt quá giới hạn cho phép."

    if "duplicate entry" in msg_l:
        return "Dữ liệu bị trùng (ví dụ: mã khóa học đã tồn tại)."

    if "foreign key constraint fails" in msg_l:
        return "Giảng viên / năm học / ngành học không hợp lệ (không tồn tại)."

    if "data truncated" in msg_l:
        return "Dữ liệu không đúng định dạng hoặc quá dài."

    return "Không thể lưu dữ liệu. Vui lòng kiểm tra lại thông tin đã nhập."
