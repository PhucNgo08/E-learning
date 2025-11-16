from sqlalchemy.orm import Session, joinedload
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from datetime import datetime
import uuid


# =========================================================
# 📋 1️⃣ Danh sách bài học theo module
# =========================================================
def list_lessons_by_module(db: Session, module_id: str):
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )


# =========================================================
# 📋 2️⃣ Danh sách tất cả bài học của giáo viên
# =========================================================
def list_lessons_by_teacher(db: Session, teacher_id: str):
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
# ➕ 3️⃣ Tạo bài học mới
# =========================================================
def create_lesson(
    db: Session,
    teacher_id: str,
    module_id: str,
    title: str,
    description: str,
    video_url: str,
    document_url: str,
    thumbnail_url: str,
):
    # 1. Kiểm tra quyền sở hữu module
    module = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Module.id == module_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not module:
        raise ValueError("Module không thuộc sở hữu của bạn.")

    # 2. Ràng buộc nội dung tối thiểu
    if not (video_url or document_url or thumbnail_url):
        raise ValueError("Cần ít nhất 1 nội dung: video / tài liệu / hình ảnh.")

    # 3. Tự động tạo lesson_number
    lesson_number = (
        db.query(Lesson).filter(Lesson.module_id == module_id).count() + 1
    )

    # 4. Tạo bài học
    lesson = Lesson(
        id=str(uuid.uuid4()),
        module_id=module_id,
        lesson_number=lesson_number,
        title=title.strip(),
        description=description.strip(),
        video_url=video_url or None,
        document_url=document_url or None,
        thumbnail_url=thumbnail_url,
        is_published=False,
        created_at=datetime.now(),
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# =========================================================
# ✏️ 4️⃣ Lấy bài học theo quyền giáo viên
# =========================================================
def get_lesson_owned(db: Session, teacher_id: str, lesson_id: str, with_module_course=False):
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

    return lesson


# =========================================================
# 💾 5️⃣ Cập nhật bài học
# =========================================================
def update_lesson(
    db: Session,
    teacher_id: str,
    lesson_id: str,
    title: str,
    description: str,
    content_type: str,
    video_url: str,
    document_url: str,
    thumbnail_url: str,
    is_published: str,
):
    # 1. Lấy bài học
    lesson = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson:
        raise ValueError("Bài học không tồn tại hoặc bạn không có quyền.")

    # 2. Xử lý giá trị boolean is_published
    publish_flag = True if str(is_published) in ["1", "true", "True", "on"] else False

    # 3. Không nội dung nào → lỗi
    if not (video_url or document_url or thumbnail_url):
        raise ValueError("Cần ít nhất 1 nội dung.")

    # 4. Cập nhật
    lesson.title = title.strip()
    lesson.description = description.strip()
    lesson.content_type = content_type
    lesson.video_url = video_url or None
    lesson.document_url = document_url or None
    lesson.thumbnail_url = thumbnail_url
    lesson.is_published = publish_flag
    lesson.updated_at = datetime.now()

    db.commit()
    db.refresh(lesson)
    return lesson.module_id


# =========================================================
# ❌ 6️⃣ Xóa bài học
# =========================================================
def delete_lesson(db: Session, teacher_id: str, lesson_id: str):
    lesson = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson:
        raise ValueError("Không thể xóa bài học không thuộc sở hữu của bạn.")

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()
    return module_id
