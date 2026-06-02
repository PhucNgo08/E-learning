import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.dependencies.auth import get_current_student
from app.services.wallet_service import (
    cancel_topup_request,
    create_topup_request,
    create_wallet,
    get_balance,
    get_student_transactions,
    get_student_topup_requests,
    get_topup_request_by_id,
    get_wallet,
    student_transfer,
    student_withdraw,
)

router = APIRouter(
    prefix="/student/wallet",
    tags=["Student Wallet"],
)

VIETQR_BANK_ID = os.getenv("VIETQR_BANK_ID", "sacombank")
VIETQR_BANK_NAME = os.getenv("VIETQR_BANK_NAME", "Sacombank")
VIETQR_ACCOUNT_NO = os.getenv("VIETQR_ACCOUNT_NO", "040109231950")
VIETQR_ACCOUNT_NAME = os.getenv("VIETQR_ACCOUNT_NAME", "LUONG HONG TIEN")
VIETQR_TEMPLATE = os.getenv("VIETQR_TEMPLATE", "compact2")

MIN_TOPUP_AMOUNT = int(os.getenv("MIN_TOPUP_AMOUNT", "10000"))
MAX_TOPUP_AMOUNT = int(os.getenv("MAX_TOPUP_AMOUNT", "50000000"))


def _normalize_amount(amount: float) -> int:
    try:
        amount_value = float(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Số tiền không hợp lệ")

    if amount_value <= 0:
        raise HTTPException(status_code=400, detail="Số tiền phải lớn hơn 0")

    if not amount_value.is_integer():
        raise HTTPException(status_code=400, detail="Số tiền phải là số nguyên VNĐ")

    amount_int = int(amount_value)

    if amount_int < MIN_TOPUP_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Số tiền nạp tối thiểu là {MIN_TOPUP_AMOUNT:,} VNĐ".replace(",", "."),
        )

    if amount_int > MAX_TOPUP_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Số tiền nạp tối đa là {MAX_TOPUP_AMOUNT:,} VNĐ".replace(",", "."),
        )

    return amount_int


def _build_vietqr_url(amount: int, transfer_code: str) -> str:
    add_info = quote(transfer_code.strip())
    account_name = quote(VIETQR_ACCOUNT_NAME.strip())

    return (
        f"https://img.vietqr.io/image/"
        f"{VIETQR_BANK_ID}-{VIETQR_ACCOUNT_NO}-{VIETQR_TEMPLATE}.png"
        f"?amount={amount}"
        f"&addInfo={add_info}"
        f"&accountName={account_name}"
    )


def wallet_common(
    request: Request,
    db: Session = Depends(get_db),
    student=Depends(get_current_student),
):
    balance = get_balance(db, student.id)

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
    topup_requests = get_student_topup_requests(
        common["db"],
        common["student"].id,
        limit=5,
    )

    return render_wallet_template(
        request,
        "wallet/index.html",
        {
            **common,
            "transactions": transactions,
            "topup_requests": topup_requests,
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


@router.post("/deposit")
def deposit_submit(
    request: Request,
    amount: float = Form(...),
    note: str = Form(""),
    common=Depends(wallet_common),
):
    try:
        amount_int = _normalize_amount(amount)
        db: Session = common["db"]
        student = common["student"]

        wallet = get_wallet(db, student.id)
        if not wallet:
            create_wallet(db, student.id)

        topup_request = create_topup_request(
            db=db,
            user_id=student.id,
            amount=amount_int,
            note=(note or "").strip() or None,
        )

        return RedirectResponse(
            f"/student/wallet/deposit/qr/{topup_request.id}",
            status_code=303,
        )

    except HTTPException as e:
        return render_wallet_template(
            request,
            "wallet/deposit.html",
            {
                **common,
                "error": e.detail,
                "form_amount": amount,
                "form_note": note,
            },
            status_code=e.status_code,
        )
    except Exception as e:
        return render_wallet_template(
            request,
            "wallet/deposit.html",
            {
                **common,
                "error": str(e),
                "form_amount": amount,
                "form_note": note,
            },
            status_code=400,
        )


@router.get("/deposit/qr/{request_id}", response_class=HTMLResponse)
def deposit_qr_page(
    request: Request,
    request_id: str,
    common=Depends(wallet_common),
):
    topup_request = get_topup_request_by_id(
        common["db"],
        request_id=request_id,
        user_id=common["student"].id,
    )

    if not topup_request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu nạp tiền")

    transfer_code = (
        getattr(topup_request, "transfer_code", None)
        or getattr(topup_request, "transfer_note", None)
        or getattr(topup_request, "request_code", None)
    )

    if not transfer_code:
        raise HTTPException(status_code=500, detail="Yêu cầu nạp tiền thiếu mã chuyển khoản")

    qr_url = _build_vietqr_url(
        amount=int(topup_request.amount),
        transfer_code=transfer_code,
    )

    return render_wallet_template(
        request,
        "wallet/deposit_qr.html",
        {
            **common,
            "topup_request": topup_request,
            "amount": int(topup_request.amount),
            "trans_code": transfer_code,
            "bank": VIETQR_BANK_NAME,
            "bank_id": VIETQR_BANK_ID,
            "account": VIETQR_ACCOUNT_NO,
            "account_name": VIETQR_ACCOUNT_NAME,
            "qr_url": qr_url,
        },
    )


@router.get("/deposit/status/{request_id}")
def deposit_status(
    request_id: str,
    common=Depends(wallet_common),
):
    topup_request = get_topup_request_by_id(
        common["db"],
        request_id=request_id,
        user_id=common["student"].id,
    )

    if not topup_request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu nạp tiền")

    transfer_code = (
        getattr(topup_request, "transfer_code", None)
        or getattr(topup_request, "transfer_note", None)
        or getattr(topup_request, "request_code", None)
    )

    admin_note = (
        getattr(topup_request, "admin_note", None)
        or getattr(topup_request, "reviewed_note", None)
    )

    reviewed_at = getattr(topup_request, "reviewed_at", None)

    return {
        "id": topup_request.id,
        "status": getattr(topup_request, "status", "pending"),
        "amount": float(getattr(topup_request, "amount", 0)),
        "transfer_code": transfer_code,
        "note": getattr(topup_request, "note", None),
        "admin_note": admin_note,
        "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
    }


@router.post("/deposit/cancel/{request_id}")
def deposit_cancel(
    request_id: str,
    common=Depends(wallet_common),
):
    try:
        cancel_topup_request(
            db=common["db"],
            request_id=request_id,
            user_id=common["student"].id,
        )
        return RedirectResponse(
            "/student/wallet/page?success=topup_cancelled",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/student/wallet/page?error={quote(str(e))}",
            status_code=303,
        )


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
        return RedirectResponse(
            "/student/wallet/page?success=withdraw",
            status_code=303,
        )
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
        return RedirectResponse(
            "/student/wallet/page?success=transfer",
            status_code=303,
        )
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