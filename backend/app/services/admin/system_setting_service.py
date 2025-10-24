from sqlalchemy.orm import Session
from datetime import datetime
from app.models.system_settings import SystemSetting

# ==============================================
# ⚙️ SERVICE: System Settings (Admin)
# ==============================================

def get_all_settings(db: Session):
    """Lấy toàn bộ cấu hình hệ thống."""
    return db.query(SystemSetting).order_by(SystemSetting.setting_key.asc()).all()


def get_setting_by_key(db: Session, key: str):
    """Lấy thông tin một cấu hình theo khóa."""
    return db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()


def update_setting(db: Session, key: str, value: str, description: str = None):
    """
    Cập nhật hoặc thêm mới cấu hình hệ thống.
    - Nếu key chưa tồn tại: tạo mới.
    - Nếu đã tồn tại: cập nhật giá trị & mô tả.
    """
    try:
        setting = get_setting_by_key(db, key)

        if not setting:
            setting = SystemSetting(
                setting_key=key,
                setting_value=value,
                description=description or "",
                created_at=datetime.utcnow(),
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

    except Exception as e:
        db.rollback()
        print(f"⚠️ Lỗi update_setting: {e}")
        raise


def delete_setting(db: Session, key: str):
    """Xóa một cấu hình hệ thống theo key."""
    try:
        setting = get_setting_by_key(db, key)
        if setting:
            db.delete(setting)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"⚠️ Lỗi delete_setting: {e}")
        raise
