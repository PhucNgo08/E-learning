from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo


def _clean_params(params: dict) -> dict:
    return {
        key: value
        for key, value in params.items()
        if value is not None
        and value != ""
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
        secret_key.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def verify_secure_hash(params: dict, secret_key: str) -> bool:
    received_hash = str(params.get("vnp_SecureHash", "")).lower()
    calculated_hash = make_secure_hash(params, secret_key).lower()

    return received_hash == calculated_hash


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

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": tmn_code,
        "vnp_Amount": str(int(Decimal(amount) * 100)),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": order_id,
        "vnp_OrderInfo": order_info,
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url,
        "vnp_IpAddr": ip_address or "127.0.0.1",
        "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": expire.strftime("%Y%m%d%H%M%S"),
    }

    params["vnp_SecureHash"] = make_secure_hash(params, secret_key)

    return f"{payment_url}?{urllib.parse.urlencode(params)}"
