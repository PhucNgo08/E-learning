from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.user import User
from app.services.wallet_service import (
    admin_adjust,
    admin_deposit,
    admin_get_all_wallets,
    admin_get_transactions,
    admin_refund,
    approve_topup_request,
    count_pending_topup_requests,
    create_wallet,
    get_admin_topup_requests,
    get_topup_request_by_id,
    get_wallet,
    reject_topup_request,
)

router = APIRouter(prefix="/admin/wallets", tags=["Admin Wallet"])


def _check_user_exists(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} không tồn tại")
    return user


@router.get("/manage", response_class=HTMLResponse)
def admin_wallet_manage(
    request: Request,
    error: str | None = None,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return templates["admin"].TemplateResponse(
        "wallet/manage.html",
        {
            "request": request,
            "error": error,
            "pending_topup_count": count_pending_topup_requests(db),
        },
    )


@router.get("/search-email", response_class=HTMLResponse)
def search_wallet_email_page(
    request: Request,
    error: str | None = None,
    admin=Depends(get_current_admin),
):
    return templates["admin"].TemplateResponse(
        "wallet/search_by_email.html",
        {"request": request, "error": error},
    )


@router.get("/search-email/process")
def search_wallet_by_email(
    request: Request,
    email: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    email = (email or "").strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return RedirectResponse(
            f"/admin/wallets/search-email?error={quote('Không tìm thấy email ' + email)}",
            status_code=303,
        )

    return RedirectResponse(
        f"/admin/wallets/info/{user.id}?success=found_by_email",
        status_code=303,
    )


@router.get("/no-wallet/{user_id}", response_class=HTMLResponse)
def admin_no_wallet_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _check_user_exists(db, user_id)
    return templates["admin"].TemplateResponse(
        "wallet/no_wallet.html",
        {"request": request, "user_id": user_id},
    )


@router.post("/create")
def admin_create_wallet(
    request: Request,
    user_id: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if wallet:
        return RedirectResponse(
            f"/admin/wallets/info/{user_id}?success=wallet_exists",
            status_code=303,
        )

    create_wallet(db, user_id)
    return RedirectResponse(
        f"/admin/wallets/info/{user_id}?success=wallet_created",
        status_code=303,
    )


@router.get("/info/{user_id}", response_class=HTMLResponse)
def admin_get_wallet_info_page(
    request: Request,
    user_id: str,
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return templates["admin"].TemplateResponse(
            "wallet/no_wallet.html",
            {"request": request, "user_id": user_id},
        )

    tx_list = admin_get_transactions(db, user_id, limit=50)
    topup_requests = get_admin_topup_requests(db, user_id=user_id, limit=20)

    return templates["admin"].TemplateResponse(
        "wallet/detail.html",
        {
            "request": request,
            "user_id": user_id,
            "user": user,
            "balance": float(wallet.balance),
            "transactions": tx_list,
            "topup_requests": topup_requests,
            "success": success,
            "error": error,
        },
    )


@router.get("/deposit", response_class=HTMLResponse)
def admin_deposit_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    error: str | None = None,
    success: str | None = None,
    admin=Depends(get_current_admin),
):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return templates["admin"].TemplateResponse(
            "wallet/no_wallet.html",
            {"request": request, "user_id": user_id},
        )

    return templates["admin"].TemplateResponse(
        "wallet/deposit.html",
        {"request": request, "user_id": user_id, "error": error, "success": success},
    )


@router.post("/deposit")
def admin_deposit_money(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin nạp tiền"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/deposit?user_id={user_id}&error={quote('User chưa có ví')}",
            status_code=303,
        )

    if amount <= 0:
        return RedirectResponse(
            f"/admin/wallets/deposit?user_id={user_id}&error={quote('Số tiền phải > 0')}",
            status_code=303,
        )

    try:
        admin_deposit(db, user_id, amount, description)
        return RedirectResponse(
            f"/admin/wallets/info/{user_id}?success=deposit",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/admin/wallets/deposit?user_id={user_id}&error={quote(str(e))}",
            status_code=303,
        )


@router.get("/refund", response_class=HTMLResponse)
def admin_refund_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    error: str | None = None,
    success: str | None = None,
    admin=Depends(get_current_admin),
):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return templates["admin"].TemplateResponse(
            "wallet/no_wallet.html",
            {"request": request, "user_id": user_id},
        )

    return templates["admin"].TemplateResponse(
        "wallet/refund.html",
        {"request": request, "user_id": user_id, "error": error, "success": success},
    )


@router.post("/refund")
def admin_refund_money(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin hoàn tiền"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/refund?user_id={user_id}&error={quote('User chưa có ví')}",
            status_code=303,
        )

    if amount <= 0:
        return RedirectResponse(
            f"/admin/wallets/refund?user_id={user_id}&error={quote('Số tiền phải > 0')}",
            status_code=303,
        )

    try:
        admin_refund(db, user_id, amount, description)
        return RedirectResponse(
            f"/admin/wallets/info/{user_id}?success=refund",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/admin/wallets/refund?user_id={user_id}&error={quote(str(e))}",
            status_code=303,
        )


@router.get("/adjust", response_class=HTMLResponse)
def admin_adjust_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    error: str | None = None,
    success: str | None = None,
    admin=Depends(get_current_admin),
):
    wallet = get_wallet(db, user_id)
    if not wallet:
        return templates["admin"].TemplateResponse(
            "wallet/no_wallet.html",
            {"request": request, "user_id": user_id},
        )

    return templates["admin"].TemplateResponse(
        "wallet/adjust.html",
        {"request": request, "user_id": user_id, "error": error, "success": success},
    )


@router.post("/adjust")
def admin_adjust_wallet(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin điều chỉnh số dư"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/adjust?user_id={user_id}&error={quote('User chưa có ví')}",
            status_code=303,
        )

    if amount == 0:
        return RedirectResponse(
            f"/admin/wallets/adjust?user_id={user_id}&error={quote('Số tiền phải khác 0')}",
            status_code=303,
        )

    try:
        admin_adjust(db, user_id, amount, description)
        return RedirectResponse(
            f"/admin/wallets/info/{user_id}?success=adjust",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/admin/wallets/adjust?user_id={user_id}&error={quote(str(e))}",
            status_code=303,
        )


@router.get("/list", response_class=HTMLResponse)
def admin_list_wallets(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    wallet_rows = admin_get_all_wallets(db)
    return templates["admin"].TemplateResponse(
        "wallet/list.html",
        {"request": request, "wallets": wallet_rows},
    )


@router.get("/topup-requests", response_class=HTMLResponse)
def admin_topup_requests_page(
    request: Request,
    status: str = "pending",
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    topup_requests = get_admin_topup_requests(db, status=status, limit=200)

    return templates["admin"].TemplateResponse(
        "wallet/topup_requests.html",
        {
            "request": request,
            "requests": topup_requests,
            "status": status,
            "success": success,
            "error": error,
            "pending_topup_count": count_pending_topup_requests(db),
        },
    )


@router.post("/topup-requests/{request_id}/approve")
def admin_approve_topup(
    request_id: str,
    reviewed_note: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    request_obj = get_topup_request_by_id(db, request_id)
    if not request_obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")

    try:
        approve_topup_request(db, request_id, admin.id, reviewed_note)
        return RedirectResponse(
            "/admin/wallets/topup-requests?status=pending&success=approved",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/admin/wallets/topup-requests?status=pending&error={quote(str(e))}",
            status_code=303,
        )


@router.post("/topup-requests/{request_id}/reject")
def admin_reject_topup(
    request_id: str,
    reviewed_note: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    request_obj = get_topup_request_by_id(db, request_id)
    if not request_obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")

    try:
        reject_topup_request(db, request_id, admin.id, reviewed_note)
        return RedirectResponse(
            "/admin/wallets/topup-requests?status=pending&success=rejected",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/admin/wallets/topup-requests?status=pending&error={quote(str(e))}",
            status_code=303,
        )