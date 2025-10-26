from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
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
        {"request": request, "lessons": lessons, "module": module, "course": course, "teacher_name": current_teacher.full_name},
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
    """Hiển thị toàn bộ bài học của giáo viên."""
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
# ➕ 3️⃣ Tạo bài học (chung hoặc theo module)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_lesson_general(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Trang tạo bài học chung (chưa chọn module)."""
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


@router.get("/create/{module_id}", response_class=HTMLResponse)
def create_lesson_page(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form tạo bài học."""
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


@router.post("/create/{module_id}")
async def create_lesson(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    video_url: str = Form(""),
    document_url: str = Form(""),
    thumbnail: UploadFile | None = File(None)
):
    """Xử lý tạo bài học."""
    teacher_id = current_teacher.id
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo bài học trong module này.")

    next_number = db.query(Lesson).filter(Lesson.module_id == module_id).count() + 1

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
        video_url=video_url.strip() or None,
        document_url=document_url.strip() or None,
        thumbnail_url=thumbnail_path,
        created_at=datetime.now()
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return RedirectResponse(f"/teacher/lessons/list/{module_id}", status_code=303)


# ======================================================
# ✏️ 4️⃣ Sửa bài học
# ======================================================
@router.get("/edit/{lesson_id}", response_class=HTMLResponse)
def edit_lesson_page(
    lesson_id: str,
    request: Request,
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
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa bài học này.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/edit.html",
        {"request": request, "lesson": lesson, "module": module, "course": course, "teacher_name": current_teacher.full_name},
    )


@router.post("/edit/{lesson_id}")
async def edit_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    video_url: str = Form(""),
    document_url: str = Form(""),
    thumbnail: UploadFile | None = File(None)
):
    """Xử lý chỉnh sửa bài học."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(
        Course.id == module.course_id, Course.teacher_id == current_teacher.id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bài học này.")

    lesson.title = title.strip()
    lesson.description = description.strip()
    lesson.video_url = video_url.strip() or None
    lesson.document_url = document_url.strip() or None

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
# ❌ 5️⃣ Xóa bài học
# ======================================================
@router.get("/delete/{lesson_id}", response_class=HTMLResponse)
def delete_lesson_page(
    lesson_id: str,
    request: Request,
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

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/delete.html",
        {"request": request, "lesson": lesson, "module": module, "course": course, "teacher_name": current_teacher.full_name},
    )


@router.post("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xử lý xóa bài học."""
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
