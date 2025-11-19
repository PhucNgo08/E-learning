from sqlalchemy import Column, String, DECIMAL, Enum, DateTime, ForeignKey, VARCHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum
import uuid


# ============================================================
# 🧩 ENUM – Loại giao dịch ví điện tử (Chuẩn 2025)
# ============================================================
class WalletTransactionType(str, enum.Enum):
    deposit = "deposit"        # + tiền (nạp thủ công / VietQR / nhận chuyển tiền)
    payment = "payment"        # - tiền (thanh toán khóa học / gửi tiền cho user khác)
    withdraw = "withdraw"      # - tiền (rút về ngân hàng)
    refund = "refund"          # + tiền (hoàn tiền giao dịch)
    adjust = "adjust"          # +/- (admin điều chỉnh số dư)


# ============================================================
# 🧩 MODEL – Lưu lịch sử giao dịch ví
# ============================================================
class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey("wallet_accounts.id", ondelete="CASCADE"), nullable=False)

    amount = Column(DECIMAL(12, 2), nullable=False)   # Số tiền thay đổi (+ hoặc -)
    type = Column(Enum(WalletTransactionType), nullable=False)  # Loại giao dịch

    description = Column(VARCHAR(255))        # Mô tả giao dịch
    balance_before = Column(DECIMAL(12, 2))   # Số dư trước khi thực hiện
    balance_after = Column(DECIMAL(12, 2))    # Số dư sau khi thực hiện

    created_at = Column(DateTime, server_default=func.now())    # Thời gian tạo

    # RELATION
    wallet = relationship("WalletAccount", back_populates="transactions")
