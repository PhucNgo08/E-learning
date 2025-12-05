"""
==========================================================
📘 app/services/course_service.py (FINAL 100% - 2025)
Tương thích đầy đủ database 2025:
- user_courses
- cart_items
- discount_percent
- class_id (nullable)

🔥 Nghiệp vụ:
- Giáo viên tạo khóa học → luôn ở trạng thái "draft"
- Giáo viên KHÔNG được tự đổi status sang "published"
- Giáo viên KHÔNG được tự bật is_public
- Admin mới có quyền publish + public
==========================================================
"""

import uuid
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session, joinedload

# ===== Models =====
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.enrollment import Enrollment
from app.models.course_review import CourseReview as Review
from app.models.cart_item import CartItem
from app.models.user_course import UserCourse


# =======================================================
# 📁 Upload Thumbnail
# =======================================================
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "course_thumbnails"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_THUMBNAIL = "/uploads/course_thumbnails/default-course.png"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

if not (UPLOAD_DIR / "default-course.png").exists():
    (UPLOAD_DIR / "default-course.png").touch()


# =======================================================
# 🔤 Helper: viết tắt môn học
# =======================================================
def _subject_abbr(subject: str) -> str:
    if not subject:
        return "CS"
    words = subject.strip().split()
    if len(words) == 1:
        return subject[:2].upper()
    return "".join(w[0].upper() for w in words[:2])


# =======================================================
# 🔢 Generate COURSE CODE - ex: CS-2025-001
# =======================================================
def generate_course_code(db: Session, subject: str) -> str:
    year = datetime.now().year
    abbr = _subject_abbr(subject)
    prefix = f"{abbr}-{year}-"

    latest = (
        db.query(Course)
        .filter(Course.course_code.like(f"{prefix}%"))
        .order_by(Course.course_code.desc())
        .first()
    )

    if not latest:
        return f"{prefix}001"

    last_no = int(latest.course_code.split("-")[-1])
    return f"{prefix}{last_no + 1:03d}"


# =======================================================
# 🏷️ 0) Tính giá cuối (có giảm giá)
# =======================================================
def get_final_price(course: Course) -> float:
    try:
        if getattr(course, "discount_percent", 0):
            return round(course.price * (100 - course.discount_percent) / 100, 2)
        return round(course.price or 0, 2)
    except:
        return course.price or 0


# =======================================================
# 🧺 0.1) Kiểm tra khóa học trong giỏ hàng
# =======================================================
def is_in_cart(db: Session, user_id: str, course_id: str) -> bool:
    return (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.course_id == course_id)
        .first()
        is not None
    )


# =======================================================
# 🛒 0.2) Kiểm tra user đã mua khóa học
# =======================================================
def is_course_purchased(db: Session, user_id: str, course_id: str) -> bool:
    return (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
        .first()
        is not None
    )


# =======================================================
# 📋 1) Danh sách khóa học
# =======================================================
def get_all_courses(db: Session, user_id: str | None, role: str, search: str | None = None):
    query = db.query(Course)

    if role == "teacher":
        query = query.filter(Course.teacher_id == user_id)

    elif role == "student":
        # 🆕 Học viên CHỈ thấy khóa học:
        # - đã publish
        # - và được public
        query = query.filter(
            Course.status == "published",
            Course.is_public == True,
        )

    if search:
        s = f"%{search}%"
        query = query.filter(
            Course.course_name.ilike(s) | Course.description.ilike(s)
        )

    courses = query.order_by(Course.created_at.desc()).all()

    # Bổ sung final_price
    for c in courses:
        c.final_price = get_final_price(c)

    return courses


# =======================================================
# 📘 2) Lấy chi tiết khóa học (FULL quyền Student 2025)
# =======================================================
def get_course_detail(db: Session, course_id: str, role: str, user_id: str | None):

    course = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.id == course_id)
        .first()
    )

    if not course:
        return None

    # ===== Student Check =====
    if role == "student" and user_id:
        # 1) Nếu đã mua => xem full
        purchased = is_course_purchased(db, user_id, course_id)
        if purchased:
            course.final_price = get_final_price(course)
            return course

        # 2) Kiểm tra enrollment
        enrolled = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.enrollment_status.in_(["approved", "active", "applied"]),
            )
            .first()
        )

        # 🆕 Nếu chưa enroll / chưa mua thì chỉ xem được khi khóa học đã publish + public
        if not enrolled and not (
            course.status == "published" and course.is_public
        ):
            return None

    course.final_price = get_final_price(course)
    return course


# =======================================================
# 🎓 3) Danh sách course_id đã đăng ký
# =======================================================
def get_enrolled_course_ids(db: Session, user_id: str) -> set[str]:
    return {
        e.course_id
        for e in db.query(Enrollment)
        .filter(
            Enrollment.user_id == user_id,
            Enrollment.enrollment_status.in_(["approved", "active", "applied"])
        )
        .all()
    }


# =======================================================
# 🎓 4) Danh sách khóa học học viên đã tham gia (tiến độ)
# =======================================================
def get_enrolled_courses(db: Session, user_id: str):
    enrolls = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.course))
        .filter(Enrollment.user_id == user_id)
        .all()
    )

    result = []
    for e in enrolls:
        total_lessons = (
            db.query(Lesson)
            .join(Module)
            .filter(Module.course_id == e.course_id)
            .count()
        )

        completed = (
            db.query(LessonProgress)
            .join(Lesson).join(Module)
            .filter(
                LessonProgress.user_id == user_id,
                Module.course_id == e.course_id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        percent = round(completed / total_lessons * 100, 1) if total_lessons else 0

        result.append({
            "course": e.course,  # đã chắc chắn không None
            "completed_lessons": completed,
            "total_lessons": total_lessons,
            "progress_percent": percent,
        })

    return result


# =======================================================
# 📈 5) Tiến độ khóa học
# =======================================================
def get_course_progress(db: Session, course_id: str, user_id: str):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return {"course": None, "modules": [], "progress": {}, "next_lesson_id": None}

    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number)
        .all()
    )

    completed_ids = {
        lp.lesson_id
        for lp in db.query(LessonProgress)
        .join(Lesson).join(Module)
        .filter(
            LessonProgress.user_id == user_id,
            Module.course_id == course_id,
            LessonProgress.progress_status == "completed"
        )
        .all()
    }

    total = 0
    done = 0
    next_lesson_id = None  # lesson đầu tiên chưa học

    for m in modules:
        for l in m.lessons:
            total += 1
            l.completed = l.id in completed_ids
            if l.completed:
                done += 1
            elif not next_lesson_id:
                next_lesson_id = l.id  # lấy lesson đầu tiên chưa học

    percent = round(done / total * 100, 1) if total else 0

    return {
        "course": course,
        "modules": modules,
        "progress": {
            "completed_lessons": done,
            "total_lessons": total,
            "percent": percent,
        },
        "next_lesson_id": next_lesson_id
    }

# =======================================================
# ⭐ 6) Reviews
# =======================================================
def get_course_feedback(db: Session, course_id: str):
    course = db.query(Course).filter(Course.id == course_id).first()
    reviews = db.query(Review).filter(Review.course_id == course_id).all()

    avg = (
        round(sum((r.overall_rating or 0) for r in reviews) / len(reviews), 1)
        if reviews else 0
    )

    return {"course": course, "reviews": reviews, "average_rating": avg}


def add_course_feedback(
    db: Session,
    course_id: str,
    user_id: str,
    title: str,
    comment: str,
    overall_rating: int,
    rating_content: int,
    rating_teacher: int,
    rating_support: int
):
    try:
        existing = (
            db.query(Review)
            .filter(Review.course_id == course_id, Review.user_id == user_id)
            .first()
        )

        if existing:
            existing.title = title.strip()
            existing.comment = comment.strip()
            existing.overall_rating = overall_rating
            existing.rating_content = rating_content
            existing.rating_teacher = rating_teacher
            existing.rating_support = rating_support
            existing.updated_at = datetime.utcnow()
            db.commit()
            return existing

        new_review = Review(
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
        return new_review

    except:
        db.rollback()
        return None


# =======================================================
# 🖼 8) Lưu thumbnail
# =======================================================
def save_thumbnail_file(thumbnail) -> str:
    try:
        if not thumbnail or not thumbnail.filename:
            return DEFAULT_THUMBNAIL

        ext = Path(thumbnail.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("Chỉ nhận JPG, PNG, GIF, WEBP")

        name = f"{uuid.uuid4().hex}{ext}"
        path = UPLOAD_DIR / name

        with open(path, "wb") as f:
            shutil.copyfileobj(thumbnail.file, f)

        return f"/uploads/course_thumbnails/{name}"

    except:
        return DEFAULT_THUMBNAIL


# =======================================================
# ➕ 9) Tạo khóa học
# =======================================================
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

    teacher_id: str | None = None,
    major_id: str | None = None,
    course_code: str | None = None,
    difficulty_level: str = "beginner",
    price: float = 0,
    discount_percent: int = 0,
    enrollment_mode: str = "auto",
    max_students: int = 100,
    academic_year_id: str | None = None,
    semester: int | None = None,
    is_public: bool = False,
    prerequisites: str | None = None,
    allow_assignments: bool = True,
    default_submission_type: str = "individual",
    status: str = "draft",   # 🆕 cho phép admin tạo khóa học đã publish nếu cần
):

    if role == "teacher":
        teacher_id = user_id

    # 🆕 Chuẩn hóa status theo role
    if role == "teacher":
        # Giáo viên luôn tạo khóa ở trạng thái "draft"
        final_status = "draft"
        final_is_public = False  # GV không tự public được khi tạo
    else:
        # Admin có thể set status nếu hợp lệ
        if status not in ("draft", "published", "archived"):
            final_status = "draft"
        else:
            final_status = status
        final_is_public = is_public

    # Check mã khóa học tồn tại
    if course_code:
        exists = db.query(Course).filter(Course.course_code == course_code).first()
        if exists:
            return {"error": "Mã khóa học đã tồn tại"}
    else:
        course_code = generate_course_code(db, subject)

    thumbnail_url = save_thumbnail_file(thumbnail)

    try:
        cr = Course(
            id=str(uuid.uuid4()),
            course_code=course_code,
            course_name=course_name.strip(),
            description=description.strip() if description else None,
            credit_hours=credit_hours,
            subject=subject,
            grade_level=grade_level,
            difficulty_level=difficulty_level,
            teacher_id=teacher_id,
            major_id=major_id,
            academic_year_id=academic_year_id,
            semester=semester,
            price=price,
            discount_percent=discount_percent,
            enrollment_mode=enrollment_mode,
            max_students=max_students,
            is_public=final_is_public,
            prerequisites=prerequisites,
            allow_assignments=1 if allow_assignments else 0,
            default_submission_type=default_submission_type,
            status=final_status,  # 🆕
            thumbnail_url=thumbnail_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(cr)
        db.commit()
        db.refresh(cr)
        cr.final_price = get_final_price(cr)
        return cr

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


# =======================================================
# ✏️ 10) Update khóa học
# =======================================================
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

    teacher_id: str | None = None,
    major_id: str | None = None,
    difficulty_level: str = "beginner",
    price: float = 0,
    discount_percent: int = 0,
    enrollment_mode: str = "auto",
    max_students: int = 100,
    academic_year_id: str | None = None,
    semester: int | None = None,
    is_public: bool = False,
    prerequisites: str | None = None,
    allow_assignments: bool = True,
    default_submission_type: str = "individual",
):

    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        return {"error": "Không có quyền chỉnh sửa"}

    # 🆕 Xử lý quyền theo role
    if role == "teacher":
        # GV không tự đổi teacher_id / major_id
        teacher_id = course.teacher_id
        major_id = course.major_id

        # GV KHÔNG được đổi status trực tiếp
        status_effective = course.status

        # GV KHÔNG được tự public (bật is_public)
        is_public_effective = course.is_public
    else:
        # Admin: được phép chỉnh status + is_public
        if status_str not in ("draft", "published", "archived"):
            status_effective = course.status
        else:
            status_effective = status_str

        is_public_effective = is_public

    try:
        course.course_name = course_name.strip()
        course.description = description.strip()
        course.credit_hours = credit_hours
        course.status = status_effective    # 🆕
        course.subject = subject
        course.grade_level = grade_level

        course.teacher_id = teacher_id
        course.major_id = major_id

        course.difficulty_level = difficulty_level
        course.price = price
        course.discount_percent = discount_percent
        course.enrollment_mode = enrollment_mode
        course.max_students = max_students
        course.academic_year_id = academic_year_id
        course.semester = semester
        course.is_public = is_public_effective  # 🆕
        course.prerequisites = prerequisites
        course.allow_assignments = 1 if allow_assignments else 0
        course.default_submission_type = default_submission_type

        if thumbnail and thumbnail.filename:
            course.thumbnail_url = save_thumbnail_file(thumbnail)

        course.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(course)

        course.final_price = get_final_price(course)
        return course

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


# =======================================================
# ❌ 11) Xóa khóa học
# =======================================================
def delete_course(db: Session, user_id: str | None, course_id: str, role: str = "admin"):
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        return False

    try:
        db.delete(course)
        db.commit()
        return True
    except:
        db.rollback()
        return False


# =======================================================
# 🔍 12) Kiểm tra khóa học thuộc giáo viên
# =======================================================
def get_course_owned(db: Session, user_id: str | None, course_id: str, role: str):
    query = db.query(Course).filter(Course.id == course_id)
    if role == "teacher":
        query = query.filter(Course.teacher_id == user_id)
    return query.first()


# =======================================================
# 🧭 13) Học viên đăng ký khóa học (HỖ TRỢ class_id)
# =======================================================
def enroll_course(db: Session, user_id: str, course_id: str, class_id: str | None = None):

    try:
        exists = db.query(Enrollment).filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
        ).first()

        if exists:
            return exists

        new_enroll = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            class_id=class_id,  # ⭐ hỗ trợ theo DB 2025
            enrollment_type="student",
            enrollment_status="applied",
            applied_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        db.add(new_enroll)

        course = db.query(Course).filter(Course.id == course_id).first()
        if course:
            course.current_students = (course.current_students or 0) + 1

        db.commit()
        db.refresh(new_enroll)
        return new_enroll

    except Exception:
        db.rollback()
        return None


# =======================================================
# 🧠 14) Kiểm tra học viên đã đăng ký (hoặc đã mua)
# =======================================================
def is_student_enrolled(db: Session, user_id: str, course_id: str) -> bool:

    # Nếu đã mua khóa học → xem luôn
    if is_course_purchased(db, user_id, course_id):
        return True

    try:
        return (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.enrollment_status.in_(["approved", "active", "applied"]),
            )
            .first()
            is not None
        )
    except:
        return False


# =======================================================
# 💡 15) Khóa học liên quan
# =======================================================
def get_related_courses(db: Session, course_id: str, limit: int = 4):
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return []

        related = (
            db.query(Course)
            .filter(
                Course.id != course_id,
                Course.status == "published",
                (
                    (Course.major_id == course.major_id) |
                    (Course.subject == course.subject) |
                    (Course.difficulty_level == course.difficulty_level)
                ),
            )
            .order_by(Course.created_at.desc())
            .limit(limit)
            .all()
        )

        for c in related:
            c.final_price = get_final_price(c)

        return related

    except:
        return []
