"""
===================================================================
💰 STUDENT WALLET ROUTER — Glass Neo 2025 (v5.0 PRO MAX)
Fix trắng trang • Auto balance • Uniform Template Data
===================================================================
"""

import uuid
from urllib.parse import quote
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
# PAGE: Deposit Form (GET)
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
# 🧾 PAGE: History
# ============================================================
@router.get("/history", response_class=HTMLResponse)
def wallet_history(
    request: Request,
    page: int = 1,
    common=Depends(wallet_common),
    success: str = None,
    error: str = None,
):
    limit = 20
    offset = (page - 1) * limit

    tx = get_student_transactions(
        common["db"], common["student"].id, limit=limit, offset=offset
    )

    return templates["student"].TemplateResponse(
        "wallet/history.html",
        {
            "request": request,
            **common,
            "transactions": tx,
            "page": page,
            "success": success,
            "error": error,
            "active_page": "wallet",
        }
    )


# ============================================================
# 🔵 API: PAY (Cart → Wallet)
# ============================================================
@router.post("/pay")
def wallet_pay(
    amount: float = Form(...),
    description: str = Form("Thanh toán khóa học"),
    common=Depends(wallet_common),
):
    try:
        tx = student_pay(common["db"], common["student"].id, amount, description)
        return {"success": True, "balance": tx.balance_after, "transaction": tx.id}
    except Exception as e:
        raise HTTPException(400, str(e))


# ============================================================
# 🟦 PAGE: QR VietQR Deposit
# ============================================================
@router.get("/deposit/qr", response_class=HTMLResponse)
def deposit_qr(
    request: Request,
    amount: float,
    common=Depends(wallet_common),
):
    if amount <= 0:
        raise HTTPException(400, "Số tiền không hợp lệ")

    student = common["student"]

    # Tạo mã giao dịch
    trans_code = f"ELEARN_{student.id[:6]}_{uuid.uuid4().hex[:6]}"

    BANK_ID = "SCB"
    ACCOUNT_NO = "040109231950"
    ACCOUNT_NAME = "LUONG HONG TIEN"

    qr_url = (
        f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact.png"
        f"?amount={int(amount)}"
        f"&addInfo={quote(trans_code)}"
        f"&accountName={quote(ACCOUNT_NAME)}"
        f"&template=compact"
    )

    return templates["student"].TemplateResponse(
        "wallet/deposit_qr.html",
        {
            "request": request,
            **common,
            "amount": amount,
            "trans_code": trans_code,
            "bank": BANK_ID,
            "account": ACCOUNT_NO,
            "account_name": ACCOUNT_NAME,
            "qr_url": qr_url,
            "active_page": "wallet",
        }
    )


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
