from sqlalchemy.orm import Session
from datetime import datetime
from app.models.system_settings import SystemSetting

# ==============================================
# ⚙️ SERVICE: System Settings
# ==============================================

def get_all_settings(db: Session):
    """Lấy toàn bộ cấu hình hệ thống"""
    return db.query(SystemSetting).order_by(SystemSetting.setting_key.asc()).all()


def get_setting_by_key(db: Session, key: str):
    """Lấy thông tin một cấu hình theo khóa"""
    return db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()


def update_setting(db: Session, key: str, value: str, description: str = None):
    """Cập nhật hoặc thêm mới cấu hình hệ thống"""
    setting = get_setting_by_key(db, key)

    if not setting:
        setting = SystemSetting(
            setting_key=key,
            setting_value=value,
            description=description or "",
            updated_at=datetime.utcnow()
        )
        db.add(setting)
    else:
        setting.setting_value = value
        if description is not None:
            setting.description = description
        setting.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(setting)
    return setting
