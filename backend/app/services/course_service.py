import uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course import Course


# =====================================================
# 📋 Lấy danh sách khóa học
# =====================================================
def get_all_courses(db: Session, user_id: str, role: str = "teacher"):
    """
    - Nếu là admin → xem tất cả khóa học.
    - Nếu là giáo viên → chỉ xem khóa học mình sở hữu.
    """
    query = db.query(Course).order_by(Course.created_at.desc())
    if role != "admin":
        query = query.filter(Course.teacher_id == user_id)
    return query.all()


# =====================================================
# 📘 Lấy khóa học theo quyền sở hữu
# =====================================================
def get_course_owned(db: Session, user_id: str, course_id: str, role: str = "teacher"):
    """
    - Admin → có thể truy cập mọi khóa học.
    - Giáo viên → chỉ truy cập khóa học của mình.
    """
    query = db.query(Course).filter(Course.id == course_id)
    if role != "admin":
        query = query.filter(Course.teacher_id == user_id)
    return query.first()


# =====================================================
# ➕ Tạo khóa học mới
# =====================================================
async def create_course(
    db: Session,
    user_id: str,
    course_name: str,
    description: str,
    credit_hours: int,
    subject: str,
    grade_level: int,
    thumbnail,
    role: str = "teacher",
):
    """Tạo mới khóa học (admin hoặc giáo viên)."""
    try:
        # Tạo course_code tự động
        course_code = f"C-{uuid.uuid4().hex[:6].upper()}"

        new_course = Course(
            id=str(uuid.uuid4()),
            course_code=course_code,
            course_name=course_name.strip(),
            description=description.strip() if description else None,
            credit_hours=credit_hours,
            subject=subject.strip() if subject else "Khác",
            grade_level=grade_level,
            teacher_id=user_id if role != "admin" else None,
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 🔹 Upload ảnh bìa (nếu có)
        if thumbnail and thumbnail.filename:
            upload_dir = Path("D:/KhoaHoctructuyen/KHoaHocOnline/uploads/course_thumbnails")
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}_{thumbnail.filename}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                f.write(await thumbnail.read())

            new_course.thumbnail_url = f"/uploads/course_thumbnails/{filename}"

        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        print(f"✅ [Tạo khóa học] {new_course.course_name}")
        return new_course

    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Lỗi tạo khóa học]:", e)
        return {"error": str(e)}


# =====================================================
# ✏️ Cập nhật khóa học
# =====================================================
async def update_course(
    db: Session,
    user_id: str,
    course_id: str,
    course_name: str,
    description: str,
    credit_hours: int,
    status_str: str,
    subject: str,
    grade_level: int,
    thumbnail,
    role: str = "teacher",
):
    """Cập nhật thông tin khóa học (admin/teacher)."""
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        return {"error": "Không tìm thấy khóa học hoặc bạn không có quyền chỉnh sửa."}

    try:
        course.course_name = course_name.strip()
        course.description = description.strip() if description else None
        course.credit_hours = credit_hours
        course.status = status_str
        course.subject = subject.strip() if subject else "Khác"
        course.grade_level = grade_level
        course.updated_at = datetime.utcnow()

        # 🔹 Upload ảnh mới (nếu có)
        if thumbnail and thumbnail.filename:
            upload_dir = Path("D:/KhoaHoctructuyen/KHoaHocOnline/uploads/course_thumbnails")
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}_{thumbnail.filename}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                f.write(await thumbnail.read())

            course.thumbnail_url = f"/uploads/course_thumbnails/{filename}"

        db.commit()
        db.refresh(course)
        print(f"✏️ [Cập nhật khóa học] {course.course_name}")
        return course

    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Lỗi cập nhật khóa học]:", e)
        return {"error": str(e)}


# =====================================================
# ❌ Xóa khóa học
# =====================================================
def delete_course(db: Session, user_id: str, course_id: str, role: str = "teacher"):
    """Xóa khóa học khỏi hệ thống (admin hoặc giáo viên)."""
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        print("⚠️ Không tìm thấy khóa học để xóa.")
        return False

    try:
        db.delete(course)
        db.commit()
        print(f"🗑️ [Xóa khóa học] {course.course_name}")
        return True

    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Lỗi xóa khóa học]:", e)
        return False
