"""
===============================================================
💰 WALLET SERVICE – OPTION A (2025 FINAL)
• KHÔNG auto-create ví trong tất cả student/admin actions
• Ví chỉ được tạo khi:
    1) Admin tạo thủ công
    2) (Tùy chọn) Student login lần đầu (nếu bạn muốn thêm)
===============================================================
"""

import uuid
from sqlalchemy.orm import Session
from app.models.wallet_accounts import WalletAccount
from app.models.wallet_transactions import WalletTransaction, WalletTransactionType
from app.models.user import User


# ============================================================
# 🔎 Lấy ví (KHÔNG tự tạo)
# ============================================================
def get_wallet(db: Session, user_id: str):
    return db.query(WalletAccount).filter_by(user_id=user_id).first()


# ============================================================
# 🟢 Tạo ví thủ công
# ============================================================
def create_wallet(db: Session, user_id: str):
    wallet = WalletAccount(
        id=str(uuid.uuid4()),
        user_id=user_id,
        balance=0
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


# ============================================================
# 🧠 Core: Tạo giao dịch
# ============================================================
def _create_transaction(
    db: Session,
    wallet: WalletAccount,
    amount: float,
    tx_type: WalletTransactionType,
    description: str = ""
):
    before = float(wallet.balance)
    after = before + amount

    # ❌ Không cho âm trừ adjust
    if after < 0 and tx_type != WalletTransactionType.adjust:
        raise Exception("❌ Số dư ví không đủ!")

    # Cập nhật ví
    wallet.balance = after

    tx = WalletTransaction(
        id=str(uuid.uuid4()),
        wallet_id=wallet.id,
        amount=amount,
        type=tx_type,
        description=description,
        balance_before=before,
        balance_after=after
    )

    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ============================================================
# 💰 Lấy số dư
# ============================================================
def get_balance(db: Session, user_id: str):
    wallet = get_wallet(db, user_id)
    return float(wallet.balance) if wallet else 0


# ============================================================
# 🔥🔥🔥 STUDENT – KHÔNG TỰ TẠO VÍ 🔥🔥🔥
# ============================================================
def student_deposit(db: Session, user_id: str, amount: float, description="Nạp tiền VietQR"):
    if amount <= 0:
        raise Exception("Số tiền nạp phải > 0")

    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, amount,
        WalletTransactionType.deposit,
        description
    )


def student_pay(db: Session, user_id: str, amount: float, description="Thanh toán khóa học"):
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, -abs(amount),
        WalletTransactionType.payment,
        description
    )


def student_withdraw(db: Session, user_id: str, amount: float, description="Rút tiền"):
    if amount <= 0:
        raise Exception("Số tiền rút phải > 0")

    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, -abs(amount),
        WalletTransactionType.withdraw,
        description
    )


def student_transfer(db: Session, sender_id: str, recipient_email: str, amount: float):
    if amount <= 0:
        raise Exception("Số tiền chuyển phải > 0")

    # Người nhận
    recipient = db.query(User).filter_by(email=recipient_email).first()
    if not recipient:
        raise Exception("Người nhận không tồn tại!")

    if recipient.id == sender_id:
        raise Exception("Không thể tự chuyển cho mình!")

    sender_wallet = get_wallet(db, sender_id)
    if not sender_wallet:
        raise Exception("Người gửi chưa có ví!")

    recipient_wallet = get_wallet(db, recipient.id)
    if not recipient_wallet:
        raise Exception("Người nhận chưa có ví!")

    sender_email = db.query(User).filter_by(id=sender_id).first().email

    # Trừ người gửi
    _create_transaction(
        db, sender_wallet, -amount,
        WalletTransactionType.transfer_out,
        f"Chuyển cho {recipient_email}"
    )

    # Cộng người nhận
    return _create_transaction(
        db, recipient_wallet, amount,
        WalletTransactionType.transfer_in,
        f"Nhận từ {sender_email}"
    )


# ============================================================
# 📜 Student – Lịch sử giao dịch
# ============================================================
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


# 🔥🔥🔥 ADMIN – KHÔNG TỰ TẠO VÍ 🔥🔥🔥
# ============================================================
def admin_adjust(db: Session, user_id: str, amount: float, description="Admin điều chỉnh"):
    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, amount,
        WalletTransactionType.adjust,
        description
    )


def admin_refund(db: Session, user_id: str, amount: float, description="Refund Order"):
    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, amount,
        WalletTransactionType.refund,
        description
    )


def admin_deposit(db: Session, user_id: str, amount: float, description="Admin nạp tiền"):
    if amount <= 0:
        raise Exception("Số tiền phải > 0")

    wallet = get_wallet(db, user_id)
    if not wallet:
        raise Exception("User chưa có ví!")

    return _create_transaction(
        db, wallet, amount,
        WalletTransactionType.deposit,
        description
    )


# ============================================================
# 📜 Admin – Lịch sử giao dịch
# ============================================================
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


# ============================================================
# 📜 Admin – Danh sách tất cả ví
# ============================================================
def admin_get_all_wallets(db: Session):
    return (
        db.query(WalletAccount, User)
        .join(User, WalletAccount.user_id == User.id)
        .order_by(WalletAccount.created_at.desc())
        .all()
    )
