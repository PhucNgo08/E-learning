"""
==========================================================
📘 app/services/course_service.py
Quản lý khóa học (dùng chung cho ADMIN, TEACHER & STUDENT)
==========================================================
"""

import uuid
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

# ===== Import Models =====
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.enrollment import Enrollment
from app.models.course_review import CourseReview as Review

# =====================================================
# 🗂️ Cấu hình thư mục upload & ảnh mặc định
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent  # → backend/app
UPLOAD_DIR = BASE_DIR / "uploads" / "course_thumbnails"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_THUMBNAIL = "/uploads/course_thumbnails/default-course.png"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

default_file = UPLOAD_DIR / "default-course.png"
if not default_file.exists():
    default_file.touch()
    print(f"⚠️ [course_service] Ảnh mặc định chưa có, đã tạo tạm: {default_file}")

print(f"📁 [course_service] Sử dụng thư mục upload: {UPLOAD_DIR}")


# =====================================================
# 📋 1️⃣ Lấy danh sách khóa học (đa quyền)
# =====================================================
def get_all_courses(
    db: Session,
    user_id: str | None = None,
    role: str = "admin",
    search: str | None = None
):
    """Trả về danh sách khóa học phù hợp với quyền người dùng"""
    query = db.query(Course)

    if role == "student":
        query = query.filter(Course.status == "published")
    elif role == "teacher" and user_id:
        query = query.filter(Course.teacher_id == user_id)

    if search:
        s = f"%{search}%"
        query = query.filter(Course.course_name.ilike(s) | Course.description.ilike(s))

    return query.order_by(Course.created_at.desc()).all()


# =====================================================
# 📘 2️⃣ Lấy chi tiết khóa học (đa quyền)
# =====================================================
def get_course_detail(db: Session, course_id: str, role: str = "student", user_id: str | None = None):
    """Lấy thông tin chi tiết của một khóa học, bao gồm modules và lessons"""
    course = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        return None

    # Học viên chỉ được xem khóa học đã public hoặc đã đăng ký
    if role == "student":
        enrolled = (
            db.query(Enrollment)
            .filter(Enrollment.course_id == course_id, Enrollment.user_id == user_id)
            .first()
            is not None
        )
        if course.status != "published" and not enrolled:
            return None

    return course


# =====================================================
# 🎓 3️⃣ Lấy danh sách khóa học học viên đã đăng ký
# =====================================================
def get_enrolled_courses(db: Session, user_id: str):
    """Lấy danh sách khóa học mà học viên đã ghi danh"""
    enrollments = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.course))
        .filter(Enrollment.user_id == user_id)
        .all()
    )

    result = []
    for e in enrollments:
        total_lessons = (
            db.query(Lesson)
            .join(Module)
            .filter(Module.course_id == e.course_id)
            .count()
        )

        completed = (
            db.query(LessonProgress)
            .join(Lesson)
            .join(Module)
            .filter(
                LessonProgress.user_id == user_id,
                Module.course_id == e.course_id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        percent = round(completed / total_lessons * 100, 1) if total_lessons else 0

        result.append(
            {
                "course": e.course,
                "completed_lessons": completed,
                "total_lessons": total_lessons,
                "progress_percent": percent,
            }
        )

    return result


# =====================================================
# 📈 4️⃣ Lấy tiến độ học tập (Student)
# =====================================================
def get_course_progress(db: Session, course_id: str, user_id: str):
    """Lấy thông tin tiến độ học của học viên trong khóa học"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return {"course": None, "modules": [], "progress": {}}

    # Lấy module + lesson
    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number)
        .all()
    )

    # Lấy danh sách bài học đã hoàn thành
    completed_lessons = {
        lp.lesson_id
        for lp in db.query(LessonProgress)
        .join(Lesson)
        .join(Module)
        .filter(
            LessonProgress.user_id == user_id,
            Module.course_id == course_id,
            LessonProgress.progress_status == "completed",
        )
        .all()
    }

    # Đánh dấu trạng thái hoàn thành cho từng bài học
    total_lessons = 0
    completed_count = 0
    for m in modules:
        for l in m.lessons:
            total_lessons += 1
            l.completed = l.id in completed_lessons  # ✅ thuộc tính động
            if l.completed:
                completed_count += 1

    # Tính phần trăm tiến độ
    percent = round(completed_count / total_lessons * 100, 1) if total_lessons else 0

    return {
        "course": course,
        "modules": modules,
        "progress": {
            "completed_lessons": completed_count,
            "total_lessons": total_lessons,
            "percent": percent,
        },
    }


# =====================================================
# 🌟 5️⃣ Lấy đánh giá khóa học (Feedback)
# =====================================================
def get_course_feedback(db: Session, course_id: str):
    """Lấy danh sách và trung bình điểm đánh giá của khóa học"""
    course = db.query(Course).filter(Course.id == course_id).first()
    reviews = db.query(Review).filter(Review.course_id == course_id).all()

    avg_rating = (
        round(sum(getattr(r, "overall_rating", 0) or 0 for r in reviews) / len(reviews), 1)
        if reviews else 0
    )

    return {"course": course, "reviews": reviews, "average_rating": avg_rating}


# =====================================================
# 💬 6️⃣ Học viên gửi đánh giá khóa học
# =====================================================
def add_course_feedback(db: Session, course_id: str, user_id: str,
                        title: str, comment: str,
                        overall_rating: int,
                        rating_content: int, rating_teacher: int, rating_support: int):
    """Học viên thêm hoặc cập nhật đánh giá khóa học"""
    from app.models.course_review import CourseReview
    try:
        # ✅ Kiểm tra học viên đã đánh giá chưa
        existing = (
            db.query(CourseReview)
            .filter(CourseReview.course_id == course_id,
                    CourseReview.user_id == user_id)
            .first()
        )

        if existing:
            # 🔁 Cập nhật đánh giá cũ
            existing.title = title.strip()
            existing.comment = comment.strip()
            existing.overall_rating = overall_rating
            existing.rating_content = rating_content
            existing.rating_teacher = rating_teacher
            existing.rating_support = rating_support
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            print(f"✏️ Học viên {user_id} đã cập nhật đánh giá cho khóa học {course_id}.")
            return existing

        # 🆕 Nếu chưa có → tạo mới
        new_review = CourseReview(
            id=str(uuid.uuid4()),
            course_id=course_id,
            user_id=user_id,
            title=title.strip(),
            comment=comment.strip(),
            overall_rating=overall_rating,
            rating_content=rating_content,
            rating_teacher=rating_teacher,
            rating_support=rating_support,
            created_at=datetime.utcnow(),
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        print(f"✅ Học viên {user_id} đã gửi đánh giá khóa học {course_id}.")
        return new_review

    except Exception as e:
        db.rollback()
        print(f"❌ [add_course_feedback] Lỗi khi thêm đánh giá: {e}")
        return None


# =====================================================
# 🧱 7️⃣ Lưu file thumbnail (Admin/Teacher)
# =====================================================
def save_thumbnail_file(thumbnail) -> str:
    """Lưu ảnh thumbnail cho khóa học"""
    try:
        if not thumbnail or not getattr(thumbnail, "filename", None):
            return DEFAULT_THUMBNAIL

        ext = Path(thumbnail.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("❌ Chỉ chấp nhận định dạng JPG, PNG, GIF, WEBP")

        file_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / file_name

        with open(file_path, "wb") as f:
            shutil.copyfileobj(thumbnail.file, f)

        print(f"🖼️ Đã lưu thumbnail: {file_path}")
        return f"/uploads/course_thumbnails/{file_name}"

    except Exception as e:
        print(f"⚠️ Lỗi lưu thumbnail: {e}")
        return DEFAULT_THUMBNAIL


# =====================================================
# ➕ 8️⃣ Tạo khóa học (Admin/Teacher)
# =====================================================
async def create_course(
    db: Session,
    user_id: str | None,
    course_name: str,
    description: str,
    credit_hours: int,
    subject: str,
    grade_level: int | None,
    thumbnail,
    role: str = "admin",
    teacher_id: str | None = None
):
    """Tạo mới khóa học"""
    try:
        course_code = f"C-{uuid.uuid4().hex[:6].upper()}"
        assigned_teacher = teacher_id if role == "admin" else user_id
        thumbnail_url = save_thumbnail_file(thumbnail)

        new_course = Course(
            id=str(uuid.uuid4()),
            course_code=course_code,
            course_name=course_name.strip(),
            description=description.strip() if description else None,
            credit_hours=credit_hours,
            subject=subject.strip() if subject else "Khác",
            grade_level=grade_level,
            teacher_id=assigned_teacher,
            status="draft",
            thumbnail_url=thumbnail_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        print(f"✅ [{role.upper()}] Tạo khóa học: {new_course.course_name}")
        return new_course

    except (SQLAlchemyError, Exception) as e:
        db.rollback()
        print(f"❌ [{role.upper()}] Lỗi tạo khóa học:", e)
        return {"error": str(e)}


# =====================================================
# ✏️ 9️⃣ Cập nhật khóa học (Admin/Teacher)
# =====================================================
async def update_course(
    db: Session,
    user_id: str | None,
    course_id: str,
    course_name: str,
    description: str,
    credit_hours: int,
    status_str: str,
    subject: str,
    grade_level: int | None,
    thumbnail,
    role: str = "admin",
    teacher_id: str | None = None
):
    """Cập nhật thông tin khóa học"""
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        return {"error": "Không tìm thấy khóa học hoặc không có quyền chỉnh sửa."}

    try:
        course.course_name = course_name.strip()
        course.description = description.strip() if description else None
        course.credit_hours = credit_hours
        course.status = status_str
        course.subject = subject.strip() if subject else "Khác"
        course.grade_level = grade_level
        course.updated_at = datetime.utcnow()

        if role == "admin" and teacher_id:
            course.teacher_id = teacher_id

        if thumbnail and getattr(thumbnail, "filename", None):
            course.thumbnail_url = save_thumbnail_file(thumbnail)

        db.commit()
        db.refresh(course)
        print(f"✏️ [{role.upper()}] Cập nhật khóa học: {course.course_name}")
        return course

    except (SQLAlchemyError, Exception) as e:
        db.rollback()
        print(f"❌ [{role.upper()}] Lỗi cập nhật khóa học:", e)
        return {"error": str(e)}


# =====================================================
# ❌ 🔟 Xóa khóa học
# =====================================================
def delete_course(db: Session, user_id: str | None, course_id: str, role: str = "admin"):
    """Xóa khóa học"""
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        print(f"⚠️ [{role.upper()}] Không tìm thấy khóa học để xóa.")
        return False

    try:
        db.delete(course)
        db.commit()
        print(f"🗑️ [{role.upper()}] Đã xóa khóa học: {course.course_name}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"❌ [{role.upper()}] Lỗi xóa khóa học:", e)
        return False


# =====================================================
# 🔍 11️⃣ Lấy khóa học theo quyền
# =====================================================
def get_course_owned(db: Session, user_id: str | None, course_id: str, role: str = "admin"):
    """Kiểm tra quyền sở hữu khóa học"""
    query = db.query(Course).filter(Course.id == course_id)
    if role == "teacher" and user_id:
        query = query.filter(Course.teacher_id == user_id)
    return query.first()


# =====================================================
# 🧭 12️⃣ Học viên đăng ký khóa học (Enroll)
# =====================================================
def enroll_course(db: Session, user_id: str, course_id: str):
    """Học viên đăng ký khóa học nếu chưa tồn tại Enrollment"""
    try:
        existing = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )
        if existing:
            print(f"⚠️ Học viên {user_id} đã đăng ký khóa học {course_id}.")
            return existing

        new_enroll = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            enrollment_status="approved",
            enrolled_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        db.add(new_enroll)
        db.commit()
        db.refresh(new_enroll)
        print(f"✅ Học viên {user_id} đăng ký thành công khóa học {course_id}.")
        return new_enroll

    except Exception as e:
        db.rollback()
        print(f"❌ [enroll_course] Lỗi đăng ký khóa học:", e)
        return None
# =====================================================
# 🧠 13️⃣ Kiểm tra học viên đã đăng ký khóa học chưa
# =====================================================
def is_student_enrolled(db: Session, user_id: str, course_id: str) -> bool:
    """
    Kiểm tra học viên đã ghi danh (enrolled) vào khóa học chưa.
    Trả về True nếu đã đăng ký, False nếu chưa.
    """
    try:
        enrolled = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.enrollment_status.in_(["approved", "active"]),
            )
            .first()
        )
        return enrolled is not None
    except Exception as e:
        print("❌ [CourseService][is_student_enrolled] Lỗi:", e)
        return False
# =====================================================
# 💡 14️⃣ Gợi ý khóa học liên quan (Student)
# =====================================================
def get_related_courses(db: Session, course_id: str, limit: int = 4):
    """
    Gợi ý các khóa học liên quan dựa theo ngành học (major_id),
    độ khó (difficulty_level), hoặc môn học (subject).
    """
    try:
        current_course = db.query(Course).filter(Course.id == course_id).first()
        if not current_course:
            return []

        related = (
            db.query(Course)
            .filter(
                Course.id != course_id,
                Course.status == "published",
                # Ưu tiên cùng ngành hoặc cùng độ khó
                (Course.major_id == current_course.major_id)
                | (Course.difficulty_level == current_course.difficulty_level)
                | (Course.subject == current_course.subject),
            )
            .order_by(Course.created_at.desc())
            .limit(limit)
            .all()
        )

        return related

    except Exception as e:
        print("❌ [CourseService][get_related_courses] Lỗi:", e)
        return []
