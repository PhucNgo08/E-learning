import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_student
from app.services.wallet_service import (
    get_balance,
    student_withdraw,
    student_transfer,
    get_student_transactions,
    find_transaction_by_code,
)
from app.config.template_config import templates


router = APIRouter(
    prefix="/student/wallet",
    tags=["Student Wallet"],
)


def wallet_common(
    request: Request,
    db: Session = Depends(get_db),
    student=Depends(get_current_student),
):
    balance = get_balance(db, student.id)

    # Đẩy dữ liệu sang request.state để layout/student_globals dùng lại
    request.state.wallet_balance = balance
    request.state.user_avatar = (
        request.session.get("user_avatar")
        or "/uploads/avatars/default-avatar.png"
    )

    return {
        "db": db,
        "student": student,
        "balance": balance,
    }


def render_wallet_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    return templates["student"].TemplateResponse(
        template_name,
        {
            "request": request,
            "active_page": "wallet",
            **context,
        },
        status_code=status_code,
    )


@router.get("/page", response_class=HTMLResponse)
def wallet_page(
    request: Request,
    common=Depends(wallet_common),
    success: str | None = None,
    error: str | None = None,
):
    transactions = get_student_transactions(
        common["db"],
        common["student"].id,
        limit=50,
    )

    return render_wallet_template(
        request,
        "wallet/index.html",
        {
            **common,
            "transactions": transactions,
            "success": success,
            "error": error,
        },
    )


@router.get("/deposit", response_class=HTMLResponse)
def deposit_page(
    request: Request,
    common=Depends(wallet_common),
    success: str | None = None,
    error: str | None = None,
):
    return render_wallet_template(
        request,
        "wallet/deposit.html",
        {
            **common,
            "success": success,
            "error": error,
        },
    )


@router.get("/deposit/qr", response_class=HTMLResponse)
def deposit_qr(
    request: Request,
    amount: float,
    common=Depends(wallet_common),
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền không hợp lệ")

    student = common["student"]
    trans_code = f"ELEARN_{student.id[:6]}_{uuid.uuid4().hex[:6]}"

    return render_wallet_template(
        request,
        "wallet/deposit_qr.html",
        {
            **common,
            "amount": amount,
            "trans_code": trans_code,
            "bank": "Sacombank",
            "account": "040109231950",
            "account_name": "LUONG HONG TIEN",
        },
    )


@router.get("/check_transaction/{trans_code}")
def check_transaction(
    trans_code: str,
    db: Session = Depends(get_db),
):
    tx = find_transaction_by_code(db, trans_code)
    return {"exists": bool(tx)}


@router.post("/deposit")
def deposit_submit(
    amount: float = Form(...),
    description: str = Form("Nạp tiền thủ công"),
    trans_code: str | None = Form(None),
    common=Depends(wallet_common),
):
    """
    Lưu ý:
    - Student KHÔNG được tự cộng ví trực tiếp.
    - Route này chỉ tiếp nhận yêu cầu nạp tiền / mã tham chiếu để chờ đối soát.
    - Khi admin xác nhận giao dịch, hệ thống mới cộng tiền vào ví.
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền nạp phải > 0")

    final_description = (description or "Nạp tiền thủ công").strip()
    if trans_code:
        final_description = f"{final_description} | Mã GD: {trans_code.strip()}"

    return {
        "success": True,
        "status": "pending_confirmation",
        "message": "Đã ghi nhận yêu cầu nạp tiền. Vui lòng chờ xác nhận giao dịch.",
        "amount": amount,
        "trans_code": (trans_code or "").strip(),
        "description": final_description,
    }


@router.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(
    request: Request,
    common=Depends(wallet_common),
    success: str | None = None,
    error: str | None = None,
):
    return render_wallet_template(
        request,
        "wallet/withdraw.html",
        {
            **common,
            "success": success,
            "error": error,
        },
    )


@router.post("/withdraw", response_class=HTMLResponse)
def withdraw_submit(
    request: Request,
    amount: float = Form(...),
    description: str = Form("Rút tiền"),
    common=Depends(wallet_common),
):
    try:
        student_withdraw(common["db"], common["student"].id, amount, description)
        return RedirectResponse("/student/wallet/page?success=withdraw", status_code=303)
    except Exception as e:
        return render_wallet_template(
            request,
            "wallet/withdraw.html",
            {
                **common,
                "error": str(e),
                "amount": amount,
            },
            status_code=400,
        )


@router.get("/transfer", response_class=HTMLResponse)
def transfer_page(
    request: Request,
    common=Depends(wallet_common),
    success: str | None = None,
    error: str | None = None,
):
    return render_wallet_template(
        request,
        "wallet/transfer.html",
        {
            **common,
            "success": success,
            "error": error,
        },
    )


@router.post("/transfer", response_class=HTMLResponse)
def transfer_submit(
    request: Request,
    recipient_email: str = Form(...),
    amount: float = Form(...),
    common=Depends(wallet_common),
):
    try:
        student_transfer(common["db"], common["student"].id, recipient_email, amount)
        return RedirectResponse("/student/wallet/page?success=transfer", status_code=303)
    except Exception as e:
        return render_wallet_template(
            request,
            "wallet/transfer.html",
            {
                **common,
                "error": str(e),
                "recipient_email": recipient_email,
                "amount": amount,
            },
            status_code=400,
        )


@router.get("/balance")
def get_wallet_balance(common=Depends(wallet_common)):
    return {"balance": common["balance"]}