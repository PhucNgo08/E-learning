import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.wallet_accounts import WalletAccount
from app.models.wallet_topup_request import WalletTopupRequest
from app.models.wallet_transactions import WalletTransaction, WalletTransactionType

TWOPLACES = Decimal("0.01")

VIETQR_BANK_ID = os.getenv("VIETQR_BANK_ID", "sacombank")
VIETQR_ACCOUNT_NO = os.getenv("VIETQR_ACCOUNT_NO", "040109231950")
VIETQR_ACCOUNT_NAME = os.getenv("VIETQR_ACCOUNT_NAME", "LUONG HONG TIEN")
TOPUP_EXPIRE_MINUTES = int(os.getenv("TOPUP_EXPIRE_MINUTES", "30"))


def _to_decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _now():
    return datetime.utcnow()


def _generate_request_code() -> str:
    return f"TOPUP-{uuid.uuid4().hex[:10].upper()}"


def _generate_transfer_note(user_id: str) -> str:
    prefix = (user_id or "").replace("-", "").upper()[:6]
    return f"ELEARN_{prefix}_{uuid.uuid4().hex[:8].upper()}"


def _normalize_topup_request(req: WalletTopupRequest | None):
    if not req:
        return None

    transfer_code = getattr(req, "transfer_code", None) or getattr(req, "transfer_note", None)
    admin_note = getattr(req, "admin_note", None) or getattr(req, "reviewed_note", None)
    created_at = getattr(req, "created_at", None) or getattr(req, "requested_at", None)

    setattr(req, "transfer_code", transfer_code)
    setattr(req, "admin_note", admin_note)
    setattr(req, "created_at", created_at)
    return req


def get_wallet(db: Session, user_id: str):
    return db.query(WalletAccount).filter(WalletAccount.user_id == user_id).first()


def create_wallet(db: Session, user_id: str):
    wallet = get_wallet(db, user_id)
    if wallet:
        return wallet

    wallet = WalletAccount(
        id=str(uuid.uuid4()),
        user_id=user_id,
        balance=_to_decimal(0),
        status="active",
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _ensure_wallet_active(wallet: WalletAccount):
    if not wallet:
        raise Exception("User chưa có ví")
    if str(wallet.status).strip().lower() != "active":
        raise Exception("Ví hiện không khả dụng")


def _apply_transaction(
    db: Session,
    wallet: WalletAccount,
    amount,
    tx_type,
    description: str = "",
    order_id: str | None = None,
):
    amount = _to_decimal(amount)
    before = _to_decimal(wallet.balance or 0)
    after = _to_decimal(before + amount)

    tx_type_value = tx_type.value if hasattr(tx_type, "value") else str(tx_type)

    if after < 0 and tx_type_value != "adjust":
        raise Exception("Số dư ví không đủ")

    wallet.balance = after

    tx = WalletTransaction(
        id=str(uuid.uuid4()),
        wallet_id=wallet.id,
        order_id=order_id,
        amount=amount,
        type=tx_type_value,
        description=(description or "").strip() or None,
        balance_before=before,
        balance_after=after,
    )
    db.add(tx)
    db.flush()
    return tx


def get_balance(db: Session, user_id: str):
    wallet = get_wallet(db, user_id)
    return float(wallet.balance) if wallet else 0.0


# =========================================================
# Student transaction flows
# =========================================================
def student_deposit(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Nạp tiền",
    order_id: str | None = None,
    auto_commit: bool = True,
):
    if float(amount) <= 0:
        raise Exception("Số tiền nạp phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            abs(float(amount)),
            WalletTransactionType.deposit,
            description,
            order_id=order_id,
        )
        if auto_commit:
            db.commit()
            db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def student_pay(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Thanh toán khóa học",
    order_id: str | None = None,
    auto_commit: bool = True,
):
    if float(amount) <= 0:
        raise Exception("Số tiền thanh toán phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            -abs(float(amount)),
            WalletTransactionType.payment,
            description,
            order_id=order_id,
        )
        if auto_commit:
            db.commit()
            db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def student_withdraw(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Rút tiền",
    auto_commit: bool = True,
):
    if float(amount) <= 0:
        raise Exception("Số tiền rút phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            -abs(float(amount)),
            WalletTransactionType.withdraw,
            description,
        )
        if auto_commit:
            db.commit()
            db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def student_transfer(
    db: Session,
    sender_id: str,
    recipient_email: str,
    amount: float,
):
    amount = float(amount)
    if amount <= 0:
        raise Exception("Số tiền chuyển phải > 0")

    recipient_email = (recipient_email or "").strip().lower()
    recipient = db.query(User).filter(User.email == recipient_email).first()
    if not recipient:
        raise Exception("Người nhận không tồn tại")

    if recipient.id == sender_id:
        raise Exception("Không thể chuyển tiền cho chính mình")

    sender = db.query(User).filter(User.id == sender_id).first()
    if not sender:
        raise Exception("Người gửi không tồn tại")

    sender_wallet = get_wallet(db, sender_id)
    recipient_wallet = get_wallet(db, recipient.id)

    _ensure_wallet_active(sender_wallet)
    _ensure_wallet_active(recipient_wallet)

    try:
        _apply_transaction(
            db,
            sender_wallet,
            -abs(amount),
            WalletTransactionType.payment,
            f"Chuyển tiền cho {recipient.email}",
        )

        received_tx = _apply_transaction(
            db,
            recipient_wallet,
            abs(amount),
            WalletTransactionType.deposit,
            f"Nhận tiền từ {sender.email}",
        )

        db.commit()
        db.refresh(received_tx)
        return received_tx
    except Exception:
        db.rollback()
        raise


def get_student_transactions(db: Session, user_id: str, limit: int = 50, offset: int = 0):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return []

    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# =========================================================
# Topup request flows
# =========================================================
def create_topup_request(
    db: Session,
    user_id: str,
    amount: float | int,
    note: str | None = None,
):
    amount_value = float(amount)
    if amount_value <= 0:
        raise Exception("Số tiền nạp phải > 0")

    wallet = get_wallet(db, user_id)
    if not wallet:
        wallet = create_wallet(db, user_id)

    request_code = _generate_request_code()
    while db.query(WalletTopupRequest).filter(WalletTopupRequest.request_code == request_code).first():
        request_code = _generate_request_code()

    transfer_note = _generate_transfer_note(user_id)
    while db.query(WalletTopupRequest).filter(WalletTopupRequest.transfer_note == transfer_note).first():
        transfer_note = _generate_transfer_note(user_id)

    req = WalletTopupRequest(
        id=str(uuid.uuid4()),
        request_code=request_code,
        user_id=user_id,
        wallet_id=wallet.id,
        amount=_to_decimal(amount_value),
        payment_channel="vietqr",
        bank_code=VIETQR_BANK_ID,
        bank_account_no=VIETQR_ACCOUNT_NO,
        bank_account_name=VIETQR_ACCOUNT_NAME,
        transfer_note=transfer_note,
        note=(note or "").strip() or None,
        status="pending",
        requested_at=_now(),
        expires_at=_now() + timedelta(minutes=TOPUP_EXPIRE_MINUTES),
    )

    db.add(req)
    db.commit()
    db.refresh(req)
    return _normalize_topup_request(req)


def get_topup_request_by_id(
    db: Session,
    request_id: str,
    user_id: str | None = None,
):
    query = db.query(WalletTopupRequest).filter(WalletTopupRequest.id == request_id)

    if user_id:
        query = query.filter(WalletTopupRequest.user_id == user_id)

    return _normalize_topup_request(query.first())


def get_student_topup_requests(
    db: Session,
    user_id: str,
    limit: int = 20,
):
    rows = (
        db.query(WalletTopupRequest)
        .filter(WalletTopupRequest.user_id == user_id)
        .order_by(WalletTopupRequest.requested_at.desc())
        .limit(limit)
        .all()
    )
    return [_normalize_topup_request(row) for row in rows]


def cancel_topup_request(
    db: Session,
    request_id: str,
    user_id: str,
):
    req = (
        db.query(WalletTopupRequest)
        .filter(
            WalletTopupRequest.id == request_id,
            WalletTopupRequest.user_id == user_id,
        )
        .first()
    )

    if not req:
        raise Exception("Không tìm thấy yêu cầu nạp tiền")

    if str(req.status).lower() != "pending":
        raise Exception("Chỉ có thể hủy yêu cầu đang chờ xác nhận")

    req.status = "cancelled"
    if hasattr(req, "reviewed_at"):
        req.reviewed_at = _now()

    db.commit()
    db.refresh(req)
    return _normalize_topup_request(req)


# =========================================================
# Admin wallet flows
# =========================================================
def admin_deposit(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Admin nạp tiền",
    order_id: str | None = None,
):
    amount = float(amount)
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            abs(amount),
            WalletTransactionType.deposit,
            description,
            order_id=order_id,
        )
        db.commit()
        db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def admin_refund(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Admin hoàn tiền",
    order_id: str | None = None,
):
    amount = float(amount)
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            abs(amount),
            WalletTransactionType.refund,
            description,
            order_id=order_id,
        )
        db.commit()
        db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def admin_adjust(
    db: Session,
    user_id: str,
    amount: float,
    description: str = "Admin điều chỉnh số dư",
):
    amount = float(amount)
    if amount == 0:
        raise Exception("Số tiền điều chỉnh phải khác 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            amount,
            WalletTransactionType.adjust,
            description,
        )
        db.commit()
        db.refresh(tx)
        return tx
    except Exception:
        db.rollback()
        raise


def admin_get_transactions(db: Session, user_id: str, limit: int = 100):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return []

    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


def admin_get_all_wallets(db: Session):
    return (
        db.query(WalletAccount, User)
        .join(User, WalletAccount.user_id == User.id)
        .order_by(WalletAccount.created_at.desc())
        .all()
    )


# =========================================================
# Admin topup review flows
# =========================================================
def get_admin_topup_requests(
    db: Session,
    status: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
):
    query = (
        db.query(WalletTopupRequest, User)
        .join(User, WalletTopupRequest.user_id == User.id)
    )

    if status and str(status).strip():
        query = query.filter(WalletTopupRequest.status == str(status).strip().lower())

    if user_id:
        query = query.filter(WalletTopupRequest.user_id == user_id)

    rows = (
        query.order_by(WalletTopupRequest.requested_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for req, user in rows:
        req = _normalize_topup_request(req)
        setattr(req, "request_user", user)
        setattr(req, "user_email", getattr(user, "email", None))
        setattr(req, "username", getattr(user, "username", None))
        items.append(req)

    return items


def count_pending_topup_requests(db: Session) -> int:
    return (
        db.query(WalletTopupRequest)
        .filter(WalletTopupRequest.status == "pending")
        .count()
    )


def approve_topup_request(
    db: Session,
    request_id: str,
    admin_id: str,
    admin_note: str | None = None,
):
    req = db.query(WalletTopupRequest).filter(WalletTopupRequest.id == request_id).first()

    if not req:
        raise Exception("Không tìm thấy yêu cầu nạp tiền")

    if str(req.status).lower() != "pending":
        raise Exception("Yêu cầu này không còn ở trạng thái chờ duyệt")

    wallet = get_wallet(db, req.user_id)
    if not wallet:
        wallet = create_wallet(db, req.user_id)

    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            abs(float(req.amount)),
            WalletTransactionType.deposit,
            f"Nạp tiền từ yêu cầu {req.transfer_note}",
        )

        req.status = "approved"
        if hasattr(req, "reviewed_note"):
            req.reviewed_note = (admin_note or "").strip() or None
        if hasattr(req, "reviewed_by"):
            req.reviewed_by = admin_id
        if hasattr(req, "reviewed_at"):
            req.reviewed_at = _now()
        if hasattr(req, "wallet_transaction_id"):
            req.wallet_transaction_id = tx.id

        db.commit()
        db.refresh(req)
        return _normalize_topup_request(req)
    except Exception:
        db.rollback()
        raise


def reject_topup_request(
    db: Session,
    request_id: str,
    admin_id: str,
    admin_note: str | None = None,
):
    req = db.query(WalletTopupRequest).filter(WalletTopupRequest.id == request_id).first()

    if not req:
        raise Exception("Không tìm thấy yêu cầu nạp tiền")

    if str(req.status).lower() != "pending":
        raise Exception("Yêu cầu này không còn ở trạng thái chờ duyệt")

    req.status = "rejected"
    if hasattr(req, "reviewed_note"):
        req.reviewed_note = (admin_note or "").strip() or None
    if hasattr(req, "reviewed_by"):
        req.reviewed_by = admin_id
    if hasattr(req, "reviewed_at"):
        req.reviewed_at = _now()

    db.commit()
    db.refresh(req)
    return _normalize_topup_request(req)


def find_transaction_by_code(db: Session, trans_code: str):
    trans_code = (trans_code or "").strip()
    if not trans_code:
        return None

    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.description.ilike(f"%{trans_code}%"))
        .order_by(WalletTransaction.created_at.desc())
        .first()
    )