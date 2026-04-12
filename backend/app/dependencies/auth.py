from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.services.common.auth_service import hydrate_user_context


def _status_is_active(user: User) -> bool:
    return str(getattr(user, "status", "active") or "active").strip().lower() in {
        "active",
        "1",
        "true",
        "enabled",
    }


def _resolved_roles(user: User) -> list[str]:
    raw_roles = getattr(user, "resolved_roles", None) or []
    roles = [str(role).strip().lower() for role in raw_roles if str(role).strip()]

    if roles:
        return roles

    single_role = getattr(user, "resolved_role", None) or getattr(user, "role", None)
    if single_role:
        return [str(single_role).strip().lower()]

    return []


def _resolved_role(user: User) -> str:
    roles = _resolved_roles(user)
    return roles[0] if roles else ""


def _resolved_permissions(user: User) -> set[str]:
    raw_permissions = getattr(user, "resolved_permissions", None) or []
    return {str(permission).strip().lower() for permission in raw_permissions if str(permission).strip()}


def _sync_session_from_user(request: Request, user: User) -> None:
    full_name = (
        getattr(user, "resolved_full_name", None)
        or getattr(user, "full_name", None)
        or getattr(user, "username", None)
        or "Người dùng"
    )
    avatar_url = (
        getattr(user, "resolved_avatar_url", None)
        or getattr(user, "avatar_url", None)
        or "/uploads/avatars/default-avatar.png"
    )

    roles = _resolved_roles(user)
    role_value = roles[0] if roles else ""

    permissions = sorted(_resolved_permissions(user))

    request.session["full_name"] = full_name
    request.session["user_full_name"] = full_name
    request.session["avatar"] = avatar_url
    request.session["user_avatar"] = avatar_url
    request.session["role"] = role_value
    request.session["user_role"] = role_value
    request.session["roles"] = roles
    request.session["user_roles"] = roles
    request.session["permissions"] = permissions
    request.session["user_permissions"] = permissions


def _ensure_role(user: User, *allowed_roles: str) -> User:
    current_roles = set(_resolved_roles(user))
    allowed = {str(role).strip().lower() for role in allowed_roles if str(role).strip()}

    if not current_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn chưa được gán vai trò hợp lệ.",
        )

    if current_roles.isdisjoint(allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập khu vực này.",
        )

    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn chưa đăng nhập.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không còn hợp lệ.",
        )

    hydrate_user_context(db, user)

    if not _status_is_active(user):
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn hiện không hoạt động.",
        )

    roles = _resolved_roles(user)
    if not roles:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản chưa được gán vai trò trong hệ thống.",
        )

    _sync_session_from_user(request, user)
    return user


def get_current_student(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    return _ensure_role(user, "student")


def get_current_teacher(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    return _ensure_role(user, "teacher", "teaching_assistant")


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    return _ensure_role(user, "admin")


def require_role(*allowed_roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        return _ensure_role(user, *allowed_roles)

    return dependency


def require_permission(permission_code: str):
    permission_code = str(permission_code or "").strip().lower()

    def dependency(user: User = Depends(get_current_user)) -> User:
        permissions = _resolved_permissions(user)
        if permission_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return user

    return dependency