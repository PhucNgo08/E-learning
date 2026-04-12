import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.academic_year import AcademicYear
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.models.user_profile import UserProfile
from app.models.major import Major
from app.models.rbac import Role


def _normalize_text(value: str) -> str:
    return (value or "").strip()


def _validate_academic_year_input(
    year_code: str,
    year_name: str,
    start_year: int,
    end_year: int,
) -> tuple[str, str, int, int]:
    year_code = _normalize_text(year_code)
    year_name = _normalize_text(year_name)

    if not year_code:
        raise ValueError("Mã năm học không được để trống.")

    if not year_name:
        raise ValueError("Tên năm học không được để trống.")

    try:
        start_year = int(start_year)
        end_year = int(end_year)
    except (TypeError, ValueError):
        raise ValueError("Năm bắt đầu và năm kết thúc phải là số hợp lệ.")

    if start_year < 2000 or end_year < 2000:
        raise ValueError("Năm bắt đầu và năm kết thúc không hợp lệ.")

    if start_year > end_year:
        raise ValueError("Năm bắt đầu không được lớn hơn năm kết thúc.")

    if end_year - start_year > 10:
        raise ValueError("Khoảng thời gian năm học không hợp lệ.")

    return year_code, year_name, start_year, end_year


# =========================================================
# CREATE
# =========================================================
def create_academic_year(
    db: Session,
    year_code: str,
    year_name: str,
    start_year: int,
    end_year: int,
    is_active: bool = True,
):
    try:
        year_code, year_name, start_year, end_year = _validate_academic_year_input(
            year_code, year_name, start_year, end_year
        )

        existing = (
            db.query(AcademicYear)
            .filter(func.lower(AcademicYear.year_code) == year_code.lower())
            .first()
        )
        if existing:
            raise ValueError(f"Mã năm học '{year_code}' đã tồn tại trong hệ thống.")

        new_year = AcademicYear(
            id=str(uuid.uuid4()),
            year_code=year_code,
            year_name=year_name,
            start_year=start_year,
            end_year=end_year,
            is_active=bool(is_active),
            created_at=datetime.now(),
        )

        db.add(new_year)
        db.commit()
        db.refresh(new_year)
        return new_year

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Mã năm học đã tồn tại trong cơ sở dữ liệu.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo năm học: {str(e)}") from e


# =========================================================
# READ
# =========================================================
def get_all_academic_years(db: Session):
    return db.query(AcademicYear).order_by(AcademicYear.start_year.desc()).all()


def get_academic_year_by_id(db: Session, year_id: str):
    return db.query(AcademicYear).filter(AcademicYear.id == year_id).first()


def get_students_by_academic_year(db: Session, year_id: str):
    return (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.email.label("email"),
            User.status.label("status"),
            StudentProfile.mssv.label("mssv"),
            UserProfile.full_name.label("full_name"),
            Major.major_name.label("major_name"),
        )
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .join(User.roles)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(Major, Major.id == StudentProfile.major_id)
        .filter(
            StudentProfile.academic_year_id == year_id,
            Role.role_code == "student",
        )
        .order_by(func.coalesce(UserProfile.full_name, User.username).asc())
        .all()
    )


# =========================================================
# UPDATE
# =========================================================
def update_academic_year(
    db: Session,
    year_id: str,
    year_code: str,
    year_name: str,
    start_year: int,
    end_year: int,
    is_active: bool,
):
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        year_code, year_name, start_year, end_year = _validate_academic_year_input(
            year_code, year_name, start_year, end_year
        )

        duplicate = (
            db.query(AcademicYear)
            .filter(
                func.lower(AcademicYear.year_code) == year_code.lower(),
                AcademicYear.id != year_id,
            )
            .first()
        )
        if duplicate:
            raise ValueError(f"Mã năm học '{year_code}' đã tồn tại.")

        year.year_code = year_code
        year.year_name = year_name
        year.start_year = start_year
        year.end_year = end_year
        year.is_active = bool(is_active)

        db.commit()
        db.refresh(year)
        return year

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Dữ liệu năm học bị trùng hoặc không hợp lệ.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật năm học: {str(e)}") from e


# =========================================================
# DELETE
# =========================================================
def delete_academic_year(db: Session, year_id: str):
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        db.delete(year)
        db.commit()
        return True

    except IntegrityError as e:
        db.rollback()
        raise ValueError("Không thể xóa năm học vì đang có dữ liệu liên kết.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa năm học: {str(e)}") from e


# =========================================================
# CHECK
# =========================================================
def is_year_code_taken(db: Session, year_code: str) -> bool:
    year_code = _normalize_text(year_code)
    if not year_code:
        return False

    return (
        db.query(AcademicYear)
        .filter(func.lower(AcademicYear.year_code) == year_code.lower())
        .first()
        is not None
    )


# =========================================================
# TOGGLE STATUS
# =========================================================
def toggle_academic_year_status(db: Session, year_id: str, active: bool):
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            return False

        year.is_active = bool(active)
        db.commit()
        db.refresh(year)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thay đổi trạng thái năm học: {str(e)}") from e