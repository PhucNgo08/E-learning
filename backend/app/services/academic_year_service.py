import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.academic_year import AcademicYear


# =========================================================
# 🧩 CREATE - Thêm năm học mới (có kiểm tra trùng)
# =========================================================
def create_academic_year(db: Session, year_code: str, year_name: str,
                         start_year: int, end_year: int, is_active: bool = True):
    """Tạo mới năm học, có kiểm tra trùng mã trước khi thêm."""
    try:
        # ✅ Kiểm tra trùng mã năm học
        existing = db.query(AcademicYear).filter(AcademicYear.year_code == year_code).first()
        if existing:
            raise ValueError(f"Mã năm học '{year_code}' đã tồn tại trong hệ thống.")

        new_year = AcademicYear(
            id=str(uuid.uuid4()),
            year_code=year_code.strip(),
            year_name=year_name.strip(),
            start_year=start_year,
            end_year=end_year,
            is_active=is_active,
            created_at=datetime.now()
        )

        db.add(new_year)
        db.commit()
        db.refresh(new_year)
        return new_year

    except ValueError:
        # ⚠️ Lỗi logic (ví dụ mã trùng)
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Mã năm học đã tồn tại trong cơ sở dữ liệu.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo năm học: {str(e)}") from e


# =========================================================
# 📋 READ - Lấy danh sách / chi tiết năm học
# =========================================================
def get_all_academic_years(db: Session):
    """Lấy tất cả năm học, sắp xếp mới nhất trước."""
    return db.query(AcademicYear).order_by(AcademicYear.start_year.desc()).all()


def get_academic_year_by_id(db: Session, year_id: str):
    """Lấy thông tin chi tiết 1 năm học theo ID."""
    return db.query(AcademicYear).filter(AcademicYear.id == year_id).first()


# =========================================================
# ✏️ UPDATE - Cập nhật năm học
# =========================================================
def update_academic_year(db: Session, year_id: str, data: dict):
    """Cập nhật thông tin năm học theo ID."""
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        # ✅ Kiểm tra trùng mã nếu đổi mã mới
        if "year_code" in data and data["year_code"] != year.year_code:
            duplicate = db.query(AcademicYear).filter(
                AcademicYear.year_code == data["year_code"],
                AcademicYear.id != year_id
            ).first()
            if duplicate:
                raise ValueError(f"Mã năm học '{data['year_code']}' đã tồn tại.")

        # ✅ Cập nhật dữ liệu
        for key, value in data.items():
            if hasattr(year, key):
                setattr(year, key, value)

        db.commit()
        db.refresh(year)
        return True

    except ValueError:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật năm học: {str(e)}") from e


# =========================================================
# 🗑️ DELETE - Xóa năm học
# =========================================================
def delete_academic_year(db: Session, year_id: str):
    """Xóa năm học theo ID."""
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        db.delete(year)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa năm học: {str(e)}") from e


# =========================================================
# 🔍 CHECK - Kiểm tra trùng mã hoặc năm học
# =========================================================
def is_year_code_taken(db: Session, year_code: str) -> bool:
    """Kiểm tra xem mã năm học đã tồn tại chưa."""
    return db.query(AcademicYear).filter(AcademicYear.year_code == year_code).first() is not None


# =========================================================
# ⚙️ Kích hoạt / vô hiệu hóa năm học
# =========================================================
def toggle_academic_year_status(db: Session, year_id: str, active: bool):
    """Kích hoạt hoặc vô hiệu hóa năm học."""
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        year.is_active = active
        db.commit()
        db.refresh(year)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thay đổi trạng thái năm học: {str(e)}") from e
