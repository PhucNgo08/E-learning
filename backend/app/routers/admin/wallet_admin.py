"""
===============================================================
💰 ADMIN WALLET ROUTER – FULL PRO VERSION 2025 (FINAL FIXED)
===============================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin
from app.database.connection import get_db
from app.config.template_config import templates

from app.models.user import User
from app.services.wallet_service import (
    get_wallet,
    admin_deposit,
    admin_adjust,
    admin_refund,
    admin_get_transactions,
    admin_get_all_wallets,
)

router = APIRouter(
    prefix="/admin/wallets",
    tags=["Admin Wallet"]
)

# ============================================================
# 🧩 Helper: kiểm tra tồn tại user
# ============================================================
def _check_user_exists(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, f"User {user_id} không tồn tại")
    return user


# ============================================================
# 🏠 PAGE: Trang quản lý ví Admin
# ============================================================
@router.get("/manage", response_class=HTMLResponse)
def admin_wallet_manage(
    request: Request,
    error: str = None,
    admin=Depends(get_current_admin)
):
    return templates["admin"].TemplateResponse(
        "wallet/manage.html",
        {
            "request": request,
            "error": error
        }
    )


# ============================================================
# 🔎 PAGE: Tìm ví theo Email (hiển thị form)
# ============================================================
@router.get("/search-email", response_class=HTMLResponse)
def search_wallet_email_page(
    request: Request,
    error: str = None,
    admin=Depends(get_current_admin)
):
    return templates["admin"].TemplateResponse(
        "wallet/search_by_email.html",
        {"request": request, "error": error}
    )


# ============================================================
# 🔎 XỬ LÝ: Tìm user theo email rồi redirect sang /info
# ============================================================
@router.get("/search-email/process", response_class=HTMLResponse)
def search_wallet_by_email(
    request: Request,
    email: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return RedirectResponse(
            f"/admin/wallets/search-email?error=Không+tìm+thấy+email+{email}",
            status_code=303
        )

    return RedirectResponse(
        f"/admin/wallets/info/{user.id}?success=found_by_email",
        status_code=303
    )


# ============================================================
# 🔍 PAGE: Xem ví qua query param /info?user_id=...
# ============================================================
@router.get("/info", response_class=HTMLResponse)
def admin_get_wallet_info_query(
    request: Request,
    user_id: str,
    success: str = None,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return admin_get_wallet_info_page(request, user_id, success, db, admin)


# ============================================================
# 🔍 PAGE: Xem ví + giao dịch
# ============================================================
@router.get("/info/{user_id}", response_class=HTMLResponse)
def admin_get_wallet_info_page(
    request: Request,
    user_id: str,
    success: str = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    balance = float(wallet.balance) if wallet else 0

    tx_list = admin_get_transactions(db, user_id, limit=50)

    return templates["admin"].TemplateResponse(
        "wallet/detail.html",
        {
            "request": request,
            "user_id": user_id,
            "balance": balance,
            "transactions": tx_list,
            "success": success
        }
    )


# ============================================================
# 🟢 GET PAGE: Hiển thị form nạp tiền
# ============================================================
@router.get("/deposit", response_class=HTMLResponse)
def admin_deposit_page(
    request: Request,
    user_id: str,
    error: str = None,
    success: str = None,
    admin=Depends(get_current_admin)
):
    return templates["admin"].TemplateResponse(
        "wallet/deposit.html",
        {
            "request": request,
            "user_id": user_id,
            "error": error,
            "success": success
        }
    )


# ============================================================
# 🟢 POST API: Nạp tiền
# ============================================================
@router.post("/deposit")
def admin_deposit_money(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin nạp tiền"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/deposit?user_id={user_id}&error=User+chưa+có+ví",
            status_code=303
        )

    if amount <= 0:
        return RedirectResponse(
            f"/admin/wallets/deposit?user_id={user_id}&error=Số+tiền+phải+>+0",
            status_code=303
        )

    admin_deposit(db, user_id, amount, description)

    return RedirectResponse(
        f"/admin/wallets/info/{user_id}?success=deposit",
        status_code=303
    )


# ============================================================
# 🟡 GET PAGE: Hiển thị form hoàn tiền
# ============================================================
@router.get("/refund", response_class=HTMLResponse)
def admin_refund_page(
    request: Request,
    user_id: str,
    error: str = None,
    success: str = None,
    admin=Depends(get_current_admin)
):
    return templates["admin"].TemplateResponse(
        "wallet/refund.html",
        {
            "request": request,
            "user_id": user_id,
            "error": error,
            "success": success
        }
    )


# ============================================================
# 🟡 POST API: Hoàn tiền
# ============================================================
@router.post("/refund")
def admin_refund_money(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin hoàn tiền"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/refund?user_id={user_id}&error=User+chưa+có+ví",
            status_code=303
        )

    if amount <= 0:
        return RedirectResponse(
            f"/admin/wallets/refund?user_id={user_id}&error=Số+tiền+phải+>+0",
            status_code=303
        )

    admin_refund(db, user_id, amount, description)

    return RedirectResponse(
        f"/admin/wallets/info/{user_id}?success=refund",
        status_code=303
    )


# ============================================================
# 🔴 GET PAGE: Hiển thị form điều chỉnh số dư
# ============================================================
@router.get("/adjust", response_class=HTMLResponse)
def admin_adjust_page(
    request: Request,
    user_id: str,
    error: str = None,
    success: str = None,
    admin=Depends(get_current_admin)
):
    return templates["admin"].TemplateResponse(
        "wallet/adjust.html",
        {
            "request": request,
            "user_id": user_id,
            "error": error,
            "success": success
        }
    )


# ============================================================
# 🔴 POST API: Điều chỉnh số dư
# ============================================================
@router.post("/adjust")
def admin_adjust_wallet(
    request: Request,
    user_id: str = Form(...),
    amount: float = Form(...),
    description: str = Form("Admin điều chỉnh số dư"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    _check_user_exists(db, user_id)

    wallet = get_wallet(db, user_id)
    if not wallet:
        return RedirectResponse(
            f"/admin/wallets/adjust?user_id={user_id}&error=User+chưa+có+ví",
            status_code=303
        )

    if amount == 0:
        return RedirectResponse(
            f"/admin/wallets/adjust?user_id={user_id}&error=Số+tiền+phải+khác+0",
            status_code=303
        )

    admin_adjust(db, user_id, amount, description)

    return RedirectResponse(
        f"/admin/wallets/info/{user_id}?success=adjust",
        status_code=303
    )


# ============================================================
# 📃 LIST: Danh sách tất cả ví
# ============================================================
@router.get("/list", response_class=HTMLResponse)
def admin_list_wallets(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    wallet_rows = admin_get_all_wallets(db)

    return templates["admin"].TemplateResponse(
        "wallet/list.html",
        {
            "request": request,
            "wallets": wallet_rows
        }
    )
