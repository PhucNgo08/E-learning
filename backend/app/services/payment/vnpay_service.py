from __future__ import annotations

import hashlib
import hmac
import re
import urllib.parse
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo


def _clean_params(params: dict) -> dict:
    return {
        str(key): str(value)
        for key, value in params.items()
        if value is not None
        and str(value) != ""
        and key not in {"vnp_SecureHash", "vnp_SecureHashType"}
    }


def build_hash_data(params: dict) -> str:
    clean = _clean_params(params)
    sorted_items = sorted(clean.items())

    return "&".join(
        f"{urllib.parse.quote_plus(str(key))}={urllib.parse.quote_plus(str(value))}"
        for key, value in sorted_items
    )


def make_secure_hash(params: dict, secret_key: str) -> str:
    hash_data = build_hash_data(params)

    return hmac.new(
        secret_key.strip().encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def verify_secure_hash(params: dict, secret_key: str) -> bool:
    received_hash = str(params.get("vnp_SecureHash", "")).strip().lower()
    if not received_hash:
        return False

    calculated_hash = make_secure_hash(params, secret_key).lower()
    return hmac.compare_digest(received_hash, calculated_hash)


def _normalize_order_info(text: str) -> str:
    
    text = (text or "Thanh Toán Khóa Học").strip()
    text = re.sub(r"[^A-Za-z0-9 ._-]", "", text)
    return text[:255] or "Thanh Toán Khóa Học"


def build_payment_url(
    *,
    payment_url: str,
    tmn_code: str,
    secret_key: str,
    return_url: str,
    order_id: str,
    amount: Decimal,
    ip_address: str,
    order_info: str,
) -> str:
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    expire = now + timedelta(minutes=15)

    amount_value = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": tmn_code.strip(),
        "vnp_Amount": str(int(amount_value * 100)),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": str(order_id),
        "vnp_OrderInfo": _normalize_order_info(order_info),
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url.strip(),
        "vnp_IpAddr": ip_address or "127.0.0.1",
        "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": expire.strftime("%Y%m%d%H%M%S"),
    }

    params["vnp_SecureHash"] = make_secure_hash(params, secret_key)

    return f"{payment_url.strip()}?{urllib.parse.urlencode(params)}"