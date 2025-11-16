from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from uuid import uuid4
from pathlib import Path

# ======================================================
# 📦 Import nội bộ
# ======================================================
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.config.template_config import get_template_by_path


# ======================================================
# 🚀 Router
# ======================================================
router = APIRouter(
    prefix="/teacher/lessons",
    tags=["Teacher - Lessons Management"]
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


# ======================================================
# 🧭 0️⃣ Redirect gốc → /list-all
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    """Truy cập /teacher/lessons sẽ tự động về /list-all"""
    return RedirectResponse("/teacher/lessons/list-all", status_code=303)


# ======================================================
# 📋 1️⃣ Danh sách bài học theo module
# ======================================================
@router.get("/list/{module_id}", response_class=HTMLResponse)
def list_lessons(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Danh sách bài học trong một module."""
    teacher_id = current_teacher.id
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem module này.")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list.html",
        {
            "request": request,
            "lessons": lessons,
            "module": module,
            "course": course,
            "teacher_name": current_teacher.full_name
        },
    )


# ======================================================
# 📚 2️⃣ Danh sách tất cả bài học của giáo viên
# ======================================================
@router.get("/list-all", response_class=HTMLResponse)
def list_all_lessons(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc(), Module.module_number.asc(), Lesson.lesson_number.asc())
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list_all.html",
        {"request": request, "lessons": lessons, "teacher_name": current_teacher.full_name},
    )


# ======================================================
# ➕ 3️⃣ Tạo bài học (GENERAL)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_lesson_general(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    modules = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc(), Module.module_number.asc())
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create_general.html",
        {"request": request, "modules": modules, "teacher_name": current_teacher.full_name},
    )


# ======================================================
# ➕ 3.1 Tạo bài học theo module
# ======================================================
@router.get("/create/{module_id}", response_class=HTMLResponse)
def create_lesson_page(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo bài học trong module này.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create.html",
        {"request": request, "module": module, "course": course, "teacher_name": current_teacher.full_name},
    )


# ======================================================
# ➕ CREATE POST
# ======================================================
@router.post("/create/{module_id}")
async def create_lesson(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    content_type: str = Form("video"),
    video_url: str = Form(""),
    document_url: str = Form(""),
    is_published: str = Form("off"),
    thumbnail: UploadFile | None = File(None)
):
    teacher_id = current_teacher.id
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    # check course ownership
    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo bài học.")

    # validate content
    if not (video_url.strip() or document_url.strip() or thumbnail):
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 nội dung (video/tài liệu/ảnh).")

    # auto lesson number
    next_number = db.query(Lesson).filter(Lesson.module_id == module_id).count() + 1

    # validate enum
    valid_types = ["video", "document", "quiz", "assignment"]
    if content_type not in valid_types:
        content_type = "document"

    publish_flag = True if is_published in ["1", "true", "True", "on"] else False

    # handle thumbnail
    thumbnail_path = None
    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{thumbnail.filename}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(await thumbnail.read())

        thumbnail_path = f"/uploads/lessons/{filename}"

    lesson = Lesson(
        id=str(uuid4()),
        module_id=module_id,
        lesson_number=next_number,
        title=title.strip(),
        description=description.strip(),
        content_type=content_type,
        video_url=video_url.strip() or None,
        document_url=document_url.strip() or None,
        thumbnail_url=thumbnail_path,
        is_published=publish_flag,
        created_at=datetime.utcnow()
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return RedirectResponse(f"/teacher/lessons/list/{module_id}", status_code=303)


# ======================================================
# ✏️ 4️⃣ EDIT PAGE
# ======================================================
@router.get("/edit/{lesson_id}", response_class=HTMLResponse)
def edit_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa bài học này.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/edit.html",
        {
            "request": request,
            "lesson": lesson,
            "module": lesson.module,
            "course": lesson.module.course,
            "teacher_name": current_teacher.full_name,
        },
    )


# ======================================================
# ✏️ 4️⃣ EDIT POST (FULL FIX)
# ======================================================
@router.post("/edit/{lesson_id}")
async def edit_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    content_type: str = Form("video"),
    video_url: str = Form(""),
    document_url: str = Form(""),
    is_published: str = Form("off"),
    thumbnail: UploadFile | None = File(None)
):

    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bài học này.")

    # validate content type ENUM
    valid_types = ["video", "document", "quiz", "assignment"]
    if content_type not in valid_types:
        content_type = lesson.content_type or "document"

    publish_flag = True if is_published in ["1", "true", "True", "on"] else False

    # validate content minimal
    if not (video_url.strip() or document_url.strip() or thumbnail):
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 nội dung (video/tài liệu/ảnh).")

    # update fields
    lesson.title = title.strip()
    lesson.description = description.strip()
    lesson.content_type = content_type
    lesson.video_url = video_url.strip() or None
    lesson.document_url = document_url.strip() or None
    lesson.is_published = publish_flag
    lesson.updated_at = datetime.utcnow()

    # upload thumbnail
    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{thumbnail.filename}"
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            f.write(await thumbnail.read())

        lesson.thumbnail_url = f"/uploads/lessons/{filename}"

    db.commit()
    db.refresh(lesson)

    return RedirectResponse(f"/teacher/lessons/list/{lesson.module_id}", status_code=303)


# ======================================================
# ❌ 5️⃣ Delete Page
# ======================================================
@router.get("/delete/{lesson_id}", response_class=HTMLResponse)
def delete_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài học này.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/delete.html",
        {
            "request": request,
            "lesson": lesson,
            "module": lesson.module,
            "course": lesson.module.course,
            "teacher_name": current_teacher.full_name
        },
    )


# ======================================================
# ❌ 5️⃣ Delete POST
# ======================================================
@router.post("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == current_teacher.id
    ).first()

    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài học này.")

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()

    return RedirectResponse(f"/teacher/lessons/list/{module_id}", status_code=303)
