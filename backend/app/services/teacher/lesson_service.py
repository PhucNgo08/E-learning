from sqlalchemy.orm import Session, joinedload
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from datetime import datetime
import uuid


# =========================================================
# 📋 Danh sách bài học theo module
# =========================================================
def list_lessons_by_module(db: Session, module_id: str):
    """
    Lấy danh sách tất cả bài học thuộc một module cụ thể.
    """
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )


# =========================================================
# 📋 Danh sách tất cả bài học của giáo viên
# =========================================================
def list_lessons_by_teacher(db: Session, teacher_id: str):
    """
    Lấy tất cả bài học thuộc các module của giáo viên.
    """
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .order_by(Lesson.created_at.desc())
        .all()
    )


# =========================================================
# ➕ Tạo bài học mới
# =========================================================
def create_lesson(
    db: Session,
    teacher_id: str,
    module_id: str,
    lesson_number: int,
    title: str,
    description: str,
    content_type: str,
    video_url: str,
    document_url: str,
    thumbnail_url: str,
):
    """
    Tạo bài học mới.
    Yêu cầu ít nhất 1 trong 3 nội dung: video_url, document_url hoặc thumbnail_url.
    """

    # Kiểm tra module có thuộc giáo viên này không
    module = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Module.id == module_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not module:
        raise ValueError("Không tìm thấy module hoặc bạn không có quyền thêm bài học vào module này.")

    # Ràng buộc nội dung bắt buộc
    if not (video_url or document_url or thumbnail_url):
        raise ValueError("Cần ít nhất 1 trong 3 nội dung: video, tài liệu hoặc hình ảnh.")

    lesson = Lesson(
        id=str(uuid.uuid4()),
        module_id=module_id,
        lesson_number=lesson_number,
        title=title,
        description=description,
        content_type=content_type,
        video_url=video_url,
        document_url=document_url,
        thumbnail_url=thumbnail_url,
        is_published=False,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# =========================================================
# ✏️ Lấy bài học (và kiểm tra quyền)
# =========================================================
def get_lesson_owned(db: Session, teacher_id: str, lesson_id: str, with_module_course=False):
    """
    Lấy bài học theo ID và kiểm tra xem giáo viên có quyền sở hữu không.
    """
    query = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
    )

    if with_module_course:
        query = query.options(
            joinedload(Lesson.module).joinedload(Module.course)
        )

    lesson = query.first()
    if not lesson:
        return None

    return (lesson, lesson.module, lesson.module.course)


# =========================================================
# 💾 Cập nhật bài học
# =========================================================
def update_lesson(
    db: Session,
    teacher_id: str,
    lesson_id: str,
    lesson_number: int,
    title: str,
    description: str,
    content_type: str,
    video_url: str,
    document_url: str,
    thumbnail_url: str,
    is_published: int,
):
    """
    Cập nhật thông tin bài học.
    """
    lesson_data = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson_data:
        return None

    # Ràng buộc: phải có ít nhất 1 nội dung
    if not (video_url or document_url or thumbnail_url):
        raise ValueError("Phải có ít nhất một nội dung (video, tài liệu hoặc hình ảnh).")

    lesson_data.lesson_number = lesson_number
    lesson_data.title = title
    lesson_data.description = description
    lesson_data.content_type = content_type
    lesson_data.video_url = video_url
    lesson_data.document_url = document_url
    lesson_data.thumbnail_url = thumbnail_url
    lesson_data.is_published = bool(is_published)
    lesson_data.updated_at = datetime.now()

    db.commit()
    db.refresh(lesson_data)
    return lesson_data.module_id


# =========================================================
# ❌ Xóa bài học
# =========================================================
def delete_lesson(db: Session, teacher_id: str, lesson_id: str):
    """
    Xóa bài học nếu giáo viên là chủ sở hữu khóa học.
    """
    lesson = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson:
        return None

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()
    return module_id
