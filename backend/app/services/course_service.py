from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.config.paths import (
    UPLOAD_COURSE_THUMBNAILS,
    build_upload_url,
    resolve_upload_path_from_url,
)
from app.models.cart_item import CartItem
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.course_review import CourseReview as Review
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.services.common.course_access_service import (
    get_accessible_course_ids as common_get_accessible_course_ids,
    get_active_course_enrollment,
    has_course_access,
)

UPLOAD_DIR = UPLOAD_COURSE_THUMBNAILS
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_THUMBNAIL = build_upload_url("course_thumbnails", "default-course.png")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

if not (UPLOAD_DIR / "default-course.png").exists():
    (UPLOAD_DIR / "default-course.png").touch()

VALID_ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}
VALID_COURSE_STATUSES = {"draft", "published", "archived"}
VALID_DIFFICULTY_LEVELS = {"beginner", "intermediate", "advanced"}
VALID_ENROLLMENT_MODES = {"auto", "approval"}
VALID_SUBMISSION_TYPES = {"individual", "group"}
VALID_ENROLLMENT_SOURCES = {"manual", "purchase", "approval", "admin", "auto"}
PURCHASE_ENROLLMENT_SOURCES = {"purchase", "wallet", "order", "paid", "vnpay", "card"}


def _subject_abbr(subject_name: str) -> str:
    if not subject_name:
        return "CS"
    words = subject_name.strip().split()
    if len(words) == 1:
        return subject_name[:2].upper()
    return "".join(w[0].upper() for w in words[:2])


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _validate_course_payload(
    course_name: str,
    credit_hours: int,
    subject_name: str,
    difficulty_level: str,
    price: float,
    discount_percent: int,
    enrollment_mode: str,
    max_students: int,
    default_submission_type: str,
) -> None:
    if not _clean_text(course_name):
        raise ValueError("Tên khóa học không được để trống.")
    if credit_hours is None or int(credit_hours) <= 0:
        raise ValueError("Số tín chỉ phải lớn hơn 0.")
    if not _clean_text(subject_name):
        raise ValueError("Môn học không được để trống.")
    if difficulty_level not in VALID_DIFFICULTY_LEVELS:
        raise ValueError("Mức độ khó không hợp lệ.")
    if price is None or float(price) < 0:
        raise ValueError("Giá khóa học không được âm.")
    if discount_percent is None or int(discount_percent) < 0 or int(discount_percent) > 100:
        raise ValueError("Phần trăm giảm giá phải nằm trong khoảng 0-100.")
    if enrollment_mode not in VALID_ENROLLMENT_MODES:
        raise ValueError("Chế độ ghi danh không hợp lệ.")
    if max_students is None or int(max_students) <= 0:
        raise ValueError("Số học viên tối đa phải lớn hơn 0.")
    if default_submission_type not in VALID_SUBMISSION_TYPES:
        raise ValueError("Kiểu nộp bài mặc định không hợp lệ.")


def _get_existing_enrollment(db: Session, user_id: str, course_id: str) -> CourseEnrollment | None:
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
        )
        .first()
    )


def generate_course_code(db: Session, subject_name: str) -> str:
    year = datetime.now().year
    abbr = _subject_abbr(subject_name)
    prefix = f"{abbr}-{year}-"
    latest = (
        db.query(Course)
        .filter(Course.course_code.like(f"{prefix}%"))
        .order_by(Course.course_code.desc())
        .first()
    )
    if not latest:
        return f"{prefix}001"
    try:
        last_no = int(str(latest.course_code).split("-")[-1])
    except Exception:
        last_no = 0
    return f"{prefix}{last_no + 1:03d}"


def get_final_price(course: Course) -> float:
    price = float(getattr(course, "price", 0) or 0)
    discount_percent = int(getattr(course, "discount_percent", 0) or 0)
    return round(price * (100 - discount_percent) / 100, 2) if discount_percent > 0 else round(price, 2)


def is_in_cart(db: Session, user_id: str, course_id: str) -> bool:
    return (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.course_id == course_id,
        )
        .first()
        is not None
    )


def can_access_course(db: Session, user_id: str, course_id: str) -> bool:
    return has_course_access(db, user_id, course_id)


def is_course_purchased(db: Session, user_id: str, course_id: str) -> bool:
    """
    Giữ lại tên hàm cũ để tránh vỡ import/router cũ.
    Nghĩa mới: có enrollment hợp lệ với source mang tính purchase hay không.
    """
    enrollment = get_active_course_enrollment(db, user_id, course_id)
    if not enrollment:
        return False

    source = (getattr(enrollment, "enrollment_source", None) or "").strip().lower()
    return source in PURCHASE_ENROLLMENT_SOURCES


def is_student_enrolled(db: Session, user_id: str, course_id: str) -> bool:
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(VALID_ACTIVE_ENROLLMENT_STATUSES),
        )
        .first()
        is not None
    )


def get_student_course_access_flags(db: Session, user_id: str, course_id: str) -> dict[str, bool]:
    enrollment = get_active_course_enrollment(db, user_id, course_id)
    if not enrollment:
        return {
            "can_access": False,
            "purchased": False,
            "enrolled": False,
        }

    source = (getattr(enrollment, "enrollment_source", None) or "").strip().lower()
    return {
        "can_access": True,
        "purchased": source in PURCHASE_ENROLLMENT_SOURCES,
        "enrolled": True,
    }


def get_purchased_course_ids(db: Session, user_id: str) -> set[str]:
    rows = (
        db.query(CourseEnrollment.course_id, CourseEnrollment.enrollment_source)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.enrollment_status.in_(VALID_ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )

    result: set[str] = set()
    for course_id, source in rows:
        if not course_id:
            continue
        if (source or "").strip().lower() in PURCHASE_ENROLLMENT_SOURCES:
            result.add(course_id)
    return result


def get_all_courses(db: Session, user_id: str | None, role: str, search: str | None = None):
    query = db.query(Course).options(joinedload(Course.teacher))

    if role == "teacher":
        query = query.filter(Course.teacher_id == user_id)
    elif role == "student":
        query = query.filter(Course.status == "published", Course.is_public.is_(True))

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Course.course_name.ilike(s) | Course.description.ilike(s))

    courses = query.order_by(Course.created_at.desc()).all()

    for course in courses:
        course.final_price = get_final_price(course)

    return courses


def get_course_detail(db: Session, course_id: str, role: str, user_id: str | None):
    course = (
        db.query(Course)
        .options(
            joinedload(Course.modules).joinedload(Module.lessons),
            joinedload(Course.teacher),
        )
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        return None

    if role == "student" and user_id:
        can_access = has_course_access(db, user_id, course_id)
        is_public_preview = course.status == "published" and bool(course.is_public)
        if not can_access and not is_public_preview:
            return None

    modules_sorted = sorted(course.modules or [], key=lambda m: (m.module_number or 0, m.created_at or datetime.min))
    for module in modules_sorted:
        module.lessons = sorted(module.lessons or [], key=lambda l: (l.lesson_number or 0, l.created_at or datetime.min))
    course.modules = modules_sorted

    course.final_price = get_final_price(course)
    return course


def get_enrolled_course_ids(db: Session, user_id: str) -> set[str]:
    return set(common_get_accessible_course_ids(db, user_id))


def get_enrolled_courses(db: Session, user_id: str):
    enrollments = (
        db.query(CourseEnrollment)
        .options(
            joinedload(CourseEnrollment.course).joinedload(Course.teacher)
        )
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.enrollment_status.in_(VALID_ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )

    result = []
    for enrollment in enrollments:
        if not enrollment.course:
            continue

        enrollment.course.final_price = get_final_price(enrollment.course)

        total_lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == enrollment.course_id)
            .count()
        )

        completed_lessons = (
            db.query(LessonProgress)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .filter(
                LessonProgress.user_id == user_id,
                Module.course_id == enrollment.course_id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0

        result.append(
            {
                "course": enrollment.course,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "progress_percent": progress_percent,
            }
        )

    result.sort(key=lambda x: (x["course"].course_name or "").lower())
    return result


def get_course_progress(db: Session, course_id: str, user_id: str):
    course = (
        db.query(Course)
        .options(joinedload(Course.teacher))
        .filter(Course.id == course_id)
        .first()
    )

    if not course:
        return {
            "course": None,
            "modules": [],
            "progress": {
                "completed_lessons": 0,
                "total_lessons": 0,
                "percent": 0,
            },
            "next_lesson_id": None,
        }

    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc())
        .all()
    )

    completed_ids = {
        lp.lesson_id
        for lp in db.query(LessonProgress)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .filter(
            LessonProgress.user_id == user_id,
            Module.course_id == course_id,
            LessonProgress.progress_status == "completed",
        )
        .all()
    }

    total_lessons = 0
    completed_lessons = 0
    next_lesson_id = None

    for module in modules:
        module.lessons = sorted(module.lessons or [], key=lambda l: (l.lesson_number or 0, l.created_at or datetime.min))

        for lesson in module.lessons:
            total_lessons += 1
            lesson.completed = lesson.id in completed_ids

            if lesson.completed:
                completed_lessons += 1
            elif next_lesson_id is None:
                next_lesson_id = lesson.id

    percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0

    return {
        "course": course,
        "modules": modules,
        "progress": {
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "percent": percent,
        },
        "next_lesson_id": next_lesson_id,
    }


def get_course_feedback(db: Session, course_id: str):
    course = (
        db.query(Course)
        .options(joinedload(Course.teacher))
        .filter(Course.id == course_id)
        .first()
    )

    reviews = (
        db.query(Review)
        .options(joinedload(Review.user))
        .filter(Review.course_id == course_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    avg = round(sum((float(r.overall_rating or 0) for r in reviews)) / len(reviews), 1) if reviews else 0

    return {
        "course": course,
        "reviews": reviews,
        "average_rating": avg,
    }


def add_course_feedback(
    db: Session,
    course_id: str,
    user_id: str,
    title: str,
    comment: str,
    overall_rating: int,
    rating_content: int,
    rating_teacher: int,
    rating_support: int,
):
    if not has_course_access(db, user_id, course_id):
        raise ValueError("Bạn cần tham gia khóa học trước khi đánh giá.")

    if int(overall_rating) < 1 or int(overall_rating) > 5:
        raise ValueError("Điểm đánh giá tổng thể phải từ 1 đến 5.")

    existing = db.query(Review).filter(
        Review.course_id == course_id,
        Review.user_id == user_id
    ).first()

    clean_title = _clean_text(title)
    clean_comment = _clean_text(comment)

    try:
        if existing:
            existing.title = clean_title
            existing.comment = clean_comment
            existing.overall_rating = overall_rating
            existing.rating_content = rating_content
            existing.rating_teacher = rating_teacher
            existing.rating_support = rating_support
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        review = Review(
            id=str(uuid.uuid4()),
            course_id=course_id,
            user_id=user_id,
            title=clean_title,
            comment=clean_comment,
            overall_rating=overall_rating,
            rating_content=rating_content,
            rating_teacher=rating_teacher,
            rating_support=rating_support,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review
    except Exception:
        db.rollback()
        raise


def save_thumbnail_file(thumbnail) -> str:
    if not thumbnail or not getattr(thumbnail, "filename", None):
        return DEFAULT_THUMBNAIL

    ext = Path(thumbnail.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Chỉ chấp nhận file ảnh JPG, JPEG, PNG, GIF, WEBP.")

    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name

    with open(path, "wb") as f:
        shutil.copyfileobj(thumbnail.file, f)

    return build_upload_url("course_thumbnails", name)


def get_course_owned(db: Session, user_id: str | None, course_id: str, role: str):
    query = db.query(Course).filter(Course.id == course_id)
    if role == "teacher":
        query = query.filter(Course.teacher_id == user_id)
    return query.first()


def delete_course(db: Session, user_id: str | None, course_id: str, role: str = "admin") -> bool:
    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        return False

    try:
        course.status = "archived"
        course.deleted_at = datetime.utcnow()

        thumbnail_url = getattr(course, "thumbnail_url", None)
        if thumbnail_url and thumbnail_url != DEFAULT_THUMBNAIL:
            thumbnail_path = resolve_upload_path_from_url(thumbnail_url)
            if thumbnail_path and thumbnail_path.exists() and thumbnail_path.is_file():
                try:
                    thumbnail_path.unlink()
                except Exception:
                    pass
            course.thumbnail_url = DEFAULT_THUMBNAIL

        db.commit()
        db.refresh(course)
        return True
    except Exception:
        db.rollback()
        raise


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
    status: str = "draft",
):
    _validate_course_payload(
        course_name,
        credit_hours,
        subject,
        difficulty_level,
        price,
        discount_percent,
        enrollment_mode,
        max_students,
        default_submission_type,
    )

    try:
        if role == "teacher":
            teacher_id = user_id
            final_status = "draft"
            final_is_public = False
        else:
            final_status = status if status in VALID_COURSE_STATUSES else "draft"
            final_is_public = bool(is_public)

        if course_code:
            course_code = course_code.strip()
            if db.query(Course).filter(Course.course_code == course_code).first():
                raise ValueError("Mã khóa học đã tồn tại.")
        else:
            course_code = generate_course_code(db, subject)

        thumbnail_url = save_thumbnail_file(thumbnail)

        course = Course(
            id=str(uuid.uuid4()),
            course_code=course_code,
            course_name=course_name.strip(),
            description=_clean_text(description),
            credit_hours=int(credit_hours),
            subject_name=subject.strip(),
            grade_level=grade_level,
            difficulty_level=difficulty_level,
            teacher_id=teacher_id,
            major_id=major_id,
            academic_year_id=academic_year_id,
            semester=semester,
            price=float(price),
            discount_percent=int(discount_percent),
            enrollment_mode=enrollment_mode,
            max_students=int(max_students),
            is_public=final_is_public,
            prerequisites=_clean_text(prerequisites),
            allow_assignments=bool(allow_assignments),
            default_submission_type=default_submission_type,
            status=final_status,
            thumbnail_url=thumbnail_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        course.final_price = get_final_price(course)
        return course
    except Exception:
        db.rollback()
        raise


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
    _validate_course_payload(
        course_name,
        credit_hours,
        subject,
        difficulty_level,
        price,
        discount_percent,
        enrollment_mode,
        max_students,
        default_submission_type,
    )

    course = get_course_owned(db, user_id, course_id, role)
    if not course:
        raise ValueError("Không có quyền chỉnh sửa khóa học này.")

    try:
        if role == "teacher":
            teacher_id = course.teacher_id
            major_id = course.major_id
            status_effective = course.status
            is_public_effective = course.is_public
        else:
            status_effective = status_str if status_str in VALID_COURSE_STATUSES else course.status
            is_public_effective = bool(is_public)

        course.course_name = course_name.strip()
        course.description = _clean_text(description)
        course.credit_hours = int(credit_hours)
        course.status = status_effective
        course.subject_name = subject.strip()
        course.grade_level = grade_level
        course.teacher_id = teacher_id
        course.major_id = major_id
        course.difficulty_level = difficulty_level
        course.price = float(price)
        course.discount_percent = int(discount_percent)
        course.enrollment_mode = enrollment_mode
        course.max_students = int(max_students)
        course.academic_year_id = academic_year_id
        course.semester = semester
        course.is_public = is_public_effective
        course.prerequisites = _clean_text(prerequisites)
        course.allow_assignments = bool(allow_assignments)
        course.default_submission_type = default_submission_type
        course.updated_at = datetime.utcnow()

        if thumbnail and getattr(thumbnail, "filename", None):
            course.thumbnail_url = save_thumbnail_file(thumbnail)

        db.commit()
        db.refresh(course)
        course.final_price = get_final_price(course)
        return course
    except Exception:
        db.rollback()
        raise


def get_related_courses(db: Session, course_id: str, limit: int = 4):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return []

    query = db.query(Course).options(joinedload(Course.teacher)).filter(
        Course.id != course_id,
        Course.status == "published",
        Course.is_public.is_(True),
    )

    if course.major_id:
        query = query.filter(Course.major_id == course.major_id)

    related = query.order_by(Course.created_at.desc()).limit(limit).all()

    for item in related:
        item.final_price = get_final_price(item)

    return related


def enroll_course(db: Session, user_id: str, course_id: str, source: str = "manual"):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")

    if course.status != "published" or not course.is_public:
        raise ValueError("Khóa học hiện chưa mở cho sinh viên đăng ký.")

    if (
        course.current_students is not None
        and course.max_students is not None
        and int(course.current_students) >= int(course.max_students)
    ):
        raise ValueError("Khóa học đã đủ số lượng học viên.")

    existing = _get_existing_enrollment(db, user_id, course_id)
    if existing:
        existing_status = (existing.enrollment_status or "").strip().lower()
        if existing_status in VALID_ACTIVE_ENROLLMENT_STATUSES:
            raise ValueError("Bạn đã đăng ký khóa học này rồi.")
        if existing_status == "applied":
            raise ValueError("Yêu cầu đăng ký của bạn đang chờ duyệt.")

    enrollment_source = source if source in VALID_ENROLLMENT_SOURCES else "manual"
    now = datetime.utcnow()
    status_value = "active" if course.enrollment_mode == "auto" else "applied"

    try:
        if existing:
            old_status = (existing.enrollment_status or "").strip().lower()

            existing.enrollment_status = status_value
            existing.enrollment_source = enrollment_source
            existing.applied_at = now
            existing.approved_at = now if status_value == "active" else None
            existing.enrolled_at = now if status_value == "active" else None
            existing.updated_at = now

            if status_value == "active" and old_status not in VALID_ACTIVE_ENROLLMENT_STATUSES:
                course.current_students = int(course.current_students or 0) + 1
                course.updated_at = now

            db.commit()
            db.refresh(existing)
            return existing

        enrollment = CourseEnrollment(
            id=str(uuid.uuid4()),
            course_id=course_id,
            user_id=user_id,
            enrollment_status=status_value,
            enrollment_source=enrollment_source,
            applied_at=now,
            approved_at=now if status_value == "active" else None,
            enrolled_at=now if status_value == "active" else None,
            created_at=now,
            updated_at=now,
        )

        db.add(enrollment)

        if status_value == "active":
            course.current_students = int(course.current_students or 0) + 1
            course.updated_at = now

        db.commit()
        db.refresh(enrollment)
        return enrollment
    except Exception:
        db.rollback()
        raise