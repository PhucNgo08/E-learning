from datetime import datetime
from sqlalchemy.orm import Session

from app.models.system_settings import SystemSetting


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _set_if_has_attr(obj, field_name: str, value):
    if hasattr(obj, field_name):
        setattr(obj, field_name, value)


def get_all_settings(db: Session):
    """Lấy toàn bộ cấu hình hệ thống."""
    return db.query(SystemSetting).order_by(SystemSetting.setting_key.asc()).all()


def get_setting_by_key(db: Session, key: str):
    """Lấy thông tin một cấu hình theo khóa."""
    key = _clean_text(key)
    if not key:
        return None
    return db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()


def update_setting(db: Session, key: str, value: str, description: str = None):
    """
    Cập nhật hoặc thêm mới cấu hình hệ thống.
    - Nếu key chưa tồn tại: tạo mới
    - Nếu đã tồn tại: cập nhật giá trị & mô tả
    """
    key = _clean_text(key)
    value = _clean_text(value)
    description = _clean_text(description)

    if not key:
        raise ValueError("Key cấu hình không được để trống.")

    try:
        setting = get_setting_by_key(db, key)
        now = datetime.utcnow()

        if not setting:
            setting = SystemSetting(
                setting_key=key,
                setting_value=value,
                description=description,
            )
            _set_if_has_attr(setting, "created_at", now)
            _set_if_has_attr(setting, "updated_at", now)
            db.add(setting)
        else:
            setting.setting_value = value
            setting.description = description
            _set_if_has_attr(setting, "updated_at", now)

        db.commit()
        db.refresh(setting)
        return setting

    except Exception as e:
        db.rollback()
        print(f"⚠️ Lỗi update_setting: {e}")
        raise


def create_setting(db: Session, key: str, value: str, description: str = None):
    """
    Tạo mới cấu hình.
    Nếu key đã tồn tại thì báo lỗi.
    """
    key = _clean_text(key)
    if not key:
        raise ValueError("Key cấu hình không được để trống.")

    existing = get_setting_by_key(db, key)
    if existing:
        raise ValueError("Key cấu hình đã tồn tại.")

    return update_setting(db, key, value, description)


def delete_setting(db: Session, key: str):
    """Xóa một cấu hình hệ thống theo key."""
    key = _clean_text(key)
    if not key:
        return False

    try:
        setting = get_setting_by_key(db, key)
        if not setting:
            return False

        db.delete(setting)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"⚠️ Lỗi delete_setting: {e}")
        raise