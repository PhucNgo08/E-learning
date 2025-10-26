from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.teacher import class_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path


# =========================================================
# 🚀 Router
# =========================================================
router = APIRouter(
    prefix="/teacher/classes",
    tags=["Teacher - Classes"]
)


# =========================================================
# 🧭 0️⃣ Redirect gốc → /list
# =========================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Truy cập /teacher/classes sẽ tự động về /list"""
    return HTMLResponse(
        content='<meta http-equiv="refresh" content="0;url=/teacher/classes/list">',
        status_code=200
    )


# =========================================================
# 📋 1️⃣ Danh sách lớp mà giáo viên phụ trách
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def class_list(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách lớp mà giáo viên phụ trách"""
    try:
        teacher_id = current_teacher.id
        classes = class_service.get_teacher_classes(db, teacher_id)

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "classes/list.html",
            {"request": request, "classes": classes, "teacher_name": current_teacher.full_name},
        )
    except Exception as e:
        print("❌ Lỗi khi tải danh sách lớp:", e)
        raise HTTPException(status_code=500, detail="Không thể tải danh sách lớp học.")


# =========================================================
# 👨‍🎓 2️⃣ Xem danh sách học viên trong lớp
# =========================================================
@router.get("/students/{class_id}", response_class=HTMLResponse)
def class_students(
    class_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách sinh viên trong lớp"""
    try:
        class_info = class_service.get_class_info(db, class_id)
        if not class_info:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")

        students = class_service.get_students_in_class(db, class_id)

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "classes/students.html",
            {
                "request": request,
                "class_info": class_info,
                "students": students,
                "teacher_name": current_teacher.full_name,
            },
        )
    except Exception as e:
        print("❌ Lỗi khi tải danh sách học viên:", e)
        raise HTTPException(status_code=500, detail="Không thể tải danh sách học viên.")
