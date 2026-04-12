import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.wallet_accounts import WalletAccount
from app.models.wallet_transactions import WalletTransaction, WalletTransactionType
from app.models.user import User


TWOPLACES = Decimal("0.01")


def _to_decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def get_wallet(db: Session, user_id: str):
    return db.query(WalletAccount).filter_by(user_id=user_id).first()


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
        raise Exception("User chưa có ví!")
    if str(wallet.status).strip().lower() == "locked":
        raise Exception("Ví đang bị khóa!")


def _apply_transaction(
    db: Session,
    wallet: WalletAccount,
    amount,
    tx_type: WalletTransactionType,
    description: str = "",
    order_id: str | None = None,
):
    amount = _to_decimal(amount)
    before = _to_decimal(wallet.balance or 0)
    after = _to_decimal(before + amount)

    if after < 0 and tx_type != WalletTransactionType.adjust:
        raise Exception("Số dư ví không đủ!")

    wallet.balance = after

    tx = WalletTransaction(
        id=str(uuid.uuid4()),
        wallet_id=wallet.id,
        order_id=order_id,
        amount=amount,
        type=tx_type.value if isinstance(tx_type, WalletTransactionType) else str(tx_type),
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


def student_deposit(
    db: Session,
    user_id: str,
    amount: float,
    description="Nạp tiền VietQR",
    order_id: str | None = None,
    auto_commit: bool = True,
):
    if amount <= 0:
        raise Exception("Số tiền nạp phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            amount,
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
    description="Thanh toán khóa học",
    order_id: str | None = None,
    auto_commit: bool = True,
):
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            -abs(amount),
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
    description="Rút tiền",
    auto_commit: bool = True,
):
    if amount <= 0:
        raise Exception("Số tiền rút phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            -abs(amount),
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


def student_transfer(db: Session, sender_id: str, recipient_email: str, amount: float):
    if amount <= 0:
        raise Exception("Số tiền chuyển phải > 0")

    recipient_email = (recipient_email or "").strip().lower()
    recipient = db.query(User).filter_by(email=recipient_email).first()
    if not recipient:
        raise Exception("Người nhận không tồn tại!")
    if recipient.id == sender_id:
        raise Exception("Không thể tự chuyển cho mình!")

    sender = db.query(User).filter_by(id=sender_id).first()
    if not sender:
        raise Exception("Người gửi không tồn tại!")

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
        receive_tx = _apply_transaction(
            db,
            recipient_wallet,
            abs(amount),
            WalletTransactionType.deposit,
            f"Nhận tiền từ {sender.email}",
        )
        db.commit()
        db.refresh(receive_tx)
        return receive_tx
    except Exception:
        db.rollback()
        raise


def get_student_transactions(db: Session, user_id: str, limit=50, offset=0):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return []

    return (
        db.query(WalletTransaction)
        .filter_by(wallet_id=wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def admin_adjust(db: Session, user_id: str, amount: float, description="Admin điều chỉnh"):
    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(db, wallet, amount, WalletTransactionType.adjust, description)
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
    description="Refund Order",
    order_id: str | None = None,
):
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            amount,
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


def admin_deposit(
    db: Session,
    user_id: str,
    amount: float,
    description="Admin nạp tiền",
    order_id: str | None = None,
):
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    _ensure_wallet_active(wallet)

    try:
        tx = _apply_transaction(
            db,
            wallet,
            amount,
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


def admin_get_transactions(db: Session, user_id: str, limit=100):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return []

    return (
        db.query(WalletTransaction)
        .filter_by(wallet_id=wallet.id)
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


def find_transaction_by_code(db: Session, trans_code: str):
    """
    Project hiện tại chưa có cột transaction_code trong wallet_transactions.
    Tạm thời đối chiếu mã tham chiếu thông qua description.
    """
    trans_code = (trans_code or "").strip()
    if not trans_code:
        return None

    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.description.ilike(f"%{trans_code}%"))
        .order_by(WalletTransaction.created_at.desc())
        .first()
    )