from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.services import course_service
from app.services.teacher import module_service
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/modules",
    tags=["Teacher - Modules Management"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/modules/list-all", status_code=303)


@router.get("/list/{course_id}", response_class=HTMLResponse)
def module_list(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    course = course_service.get_course_owned(db, current_teacher.id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc bạn không có quyền truy cập.")

    modules = module_service.list_modules_by_course(db, course_id)

    return render_template(
        request,
        "modules/list.html",
        {
            "teacher": current_teacher,
            "course": course,
            "modules": modules or [],
            "page_title": f"📚 Danh sách module - {course.course_name}",
        },
    )


@router.get("/list-all", response_class=HTMLResponse)
def list_all_modules(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    modules = module_service.list_all_modules_by_teacher(db, current_teacher.id)

    return render_template(
        request,
        "modules/list_all.html",
        {
            "teacher": current_teacher,
            "modules": modules,
            "page_title": "📘 Tất cả module của bạn",
        },
    )


@router.get("/create/{course_id}", response_class=HTMLResponse)
def page_create(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    course = course_service.get_course_owned(db, current_teacher.id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc bạn không có quyền truy cập.")

    return render_template(
        request,
        "modules/create.html",
        {
            "teacher": current_teacher,
            "course": course,
            "page_title": f"➕ Thêm module cho {course.course_name}",
        },
    )


@router.post("/create/{course_id}")
def create_module(
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form(""),
):
    result = module_service.create_module(
        db, current_teacher.id, course_id, module_number, title, description, learning_objectives
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)


@router.get("/edit/{module_id}", response_class=HTMLResponse)
def page_edit(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    module, course = module_service.get_module_owned_with_course(db, current_teacher.id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền chỉnh sửa.")

    return render_template(
        request,
        "modules/edit.html",
        {
            "teacher": current_teacher,
            "module": module,
            "course": course,
            "page_title": f"✏️ Chỉnh sửa module: {module.title}",
        },
    )


@router.post("/edit/{module_id}")
def edit_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form(""),
):
    result = module_service.update_module(
        db, current_teacher.id, module_id, module_number, title, description, learning_objectives
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(f"/teacher/modules/list/{result['course_id']}", status_code=303)


@router.get("/delete/{module_id}", response_class=HTMLResponse)
def page_delete(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    module, course = module_service.get_module_owned_with_course(db, current_teacher.id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xóa.")

    return render_template(
        request,
        "modules/delete.html",
        {
            "teacher": current_teacher,
            "module": module,
            "course": course,
            "page_title": f"🗑️ Xóa module: {module.title}",
        },
    )


@router.post("/delete/{module_id}", response_class=HTMLResponse)
def delete_module(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    module, course = module_service.get_module_owned_with_course(db, current_teacher.id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xóa.")

    result = module_service.delete_module(db, current_teacher.id, module_id)

    if "error" in result:
        return render_template(
            request,
            "modules/delete.html",
            {
                "teacher": current_teacher,
                "module": module,
                "course": course,
                "error_msg": result["error"],
                "page_title": f"🗑️ Xóa module: {module.title}",
            },
            status_code=400,
        )

    return RedirectResponse(f"/teacher/modules/list/{result['course_id']}", status_code=303)


@router.post("/publish/{module_id}")
def publish_module(
    module_id: str,
    publish: bool = True,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    result = module_service.publish_module(db, current_teacher.id, module_id, publish)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(f"/teacher/modules/list/{result['module'].course_id}", status_code=303)