"""
===================================================================
💰 STUDENT WALLET ROUTER — Glass Neo 2025 (v6.0 PRO MAX)
QR Tĩnh • Không phụ thuộc API ngoài • Auto-balance • Auto-check
===================================================================
"""

import uuid
from fastapi import (
    APIRouter, Depends, Request, HTTPException, Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_student

from app.services.wallet_service import (
    get_balance,
    student_pay,
    student_deposit,
    student_withdraw,
    student_transfer,
    get_student_transactions
)

from app.config.template_config import templates


router = APIRouter(
    prefix="/student/wallet",
    tags=["Student Wallet"]
)


# ============================================================
# ⭐ DEPENDENCY DÙNG CHUNG
# ============================================================
def wallet_common(
    db: Session = Depends(get_db),
    student=Depends(get_current_student)
):
    """Trả về student + balance dùng cho mọi trang."""
    balance = get_balance(db, student.id)
    return {"db": db, "student": student, "balance": balance}


# ============================================================
# 🧾 PAGE: Wallet Home
# ============================================================
@router.get("/page", response_class=HTMLResponse)
def wallet_page(
    request: Request,
    common=Depends(wallet_common),
    success: str = None,
    error: str = None,
):
    tx = get_student_transactions(common["db"], common["student"].id, limit=50)

    return templates["student"].TemplateResponse(
        "wallet/index.html",
        {
            "request": request,
            **common,
            "transactions": tx,
            "success": success,
            "error": error,
            "active_page": "wallet",
        }
    )


# ============================================================
# PAGE: Deposit Form
# ============================================================
@router.get("/deposit", response_class=HTMLResponse)
def deposit_page(
    request: Request,
    common=Depends(wallet_common),
    success: str = None,
    error: str = None,
):
    return templates["student"].TemplateResponse(
        "wallet/deposit.html",
        {
            "request": request,
            **common,
            "success": success,
            "error": error,
            "active_page": "wallet",
        }
    )


# ============================================================
# 🟦 PAGE: Deposit QR — Static QR Image
# ============================================================
@router.get("/deposit/qr", response_class=HTMLResponse)
def deposit_qr(
    request: Request,
    amount: float,
    common=Depends(wallet_common)
):
    if amount <= 0:
        raise HTTPException(400, "Số tiền không hợp lệ")

    student = common["student"]

    # 🔐 Tạo mã giao dịch duy nhất
    trans_code = f"ELEARN_{student.id[:6]}_{uuid.uuid4().hex[:6]}"

    # 💳 Thông tin hiển thị
    BANK_NAME = "Sacombank"
    ACCOUNT_NO = "040109231950"
    ACCOUNT_NAME = "LUONG HONG TIEN"

    # 🔥 Không có qr_url – dùng hình tĩnh trong static/QR/
    return templates["student"].TemplateResponse(
        "wallet/deposit_qr.html",
        {
            "request": request,
            **common,
            "amount": amount,
            "trans_code": trans_code,
            "bank": BANK_NAME,
            "account": ACCOUNT_NO,
            "account_name": ACCOUNT_NAME,
            "active_page": "wallet",
        }
    )


# ============================================================
# 🟧 API: Check if transaction completed (Auto-check)
# ============================================================
@router.get("/check_transaction/{trans_code}")
def check_transaction(trans_code: str, db: Session = Depends(get_db)):
    from app.models.wallet import WalletTransaction

    tx = db.query(WalletTransaction).filter_by(transaction_code=trans_code).first()

    return {"exists": bool(tx)}


# ============================================================
# 🟢 API: Deposit Manual
# ============================================================
@router.post("/deposit")
def deposit_submit(
    amount: float = Form(...),
    description: str = Form("Nạp tiền thủ công"),
    common=Depends(wallet_common),
):
    try:
        tx = student_deposit(common["db"], common["student"].id, amount, description)
        return {"success": True, "balance": tx.balance_after}
    except Exception as e:
        raise HTTPException(400, str(e))


# ============================================================
# 💸 PAGE: Withdraw
# ============================================================
@router.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(
    request: Request,
    common=Depends(wallet_common),
    success: str = None,
    error: str = None,
):
    return templates["student"].TemplateResponse(
        "wallet/withdraw.html",
        {
            "request": request,
            **common,
            "success": success,
            "error": error,
            "active_page": "wallet",
        }
    )


# ============================================================
# 💸 API: Withdraw Submit
# ============================================================
@router.post("/withdraw", response_class=HTMLResponse)
def withdraw_submit(
    request: Request,
    amount: float = Form(...),
    description: str = Form("Rút tiền"),
    common=Depends(wallet_common),
):
    try:
        student_withdraw(common["db"], common["student"].id, amount, description)
        return RedirectResponse("/student/wallet/page?success=withdraw", 303)

    except Exception as e:
        return templates["student"].TemplateResponse(
            "wallet/withdraw.html",
            {
                "request": request,
                **common,
                "error": str(e),
                "amount": amount,
                "active_page": "wallet",
            }
        )


# ============================================================
# 🔁 PAGE: Transfer
# ============================================================
@router.get("/transfer", response_class=HTMLResponse)
def transfer_page(
    request: Request,
    common=Depends(wallet_common),
    success: str = None,
    error: str = None,
):
    return templates["student"].TemplateResponse(
        "wallet/transfer.html",
        {
            "request": request,
            **common,
            "success": success,
            "error": error,
            "active_page": "wallet",
        }
    )


# ============================================================
# 🔁 API: Transfer Submit
# ============================================================
@router.post("/transfer", response_class=HTMLResponse)
def transfer_submit(
    request: Request,
    recipient_email: str = Form(...),
    amount: float = Form(...),
    common=Depends(wallet_common),
):
    try:
        student_transfer(
            common["db"], common["student"].id,
            recipient_email, amount
        )
        return RedirectResponse("/student/wallet/page?success=transfer", 303)

    except Exception as e:
        return templates["student"].TemplateResponse(
            "wallet/transfer.html",
            {
                "request": request,
                **common,
                "error": str(e),
                "recipient_email": recipient_email,
                "amount": amount,
                "active_page": "wallet",
            }
        )


# ============================================================
# 🟦 API: Get current balance (Auto refresh every 3s)
# ============================================================
@router.get("/balance")
def get_wallet_balance(common=Depends(wallet_common)):
    return {"balance": common["balance"]}
