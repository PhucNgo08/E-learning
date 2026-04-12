from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.teacher import class_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/classes",
    tags=["Teacher - Classes"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/classes/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def class_list(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        classes = class_service.get_teacher_classes(db, current_teacher.id)

        return render_template(
            request,
            "classes/list.html",
            {
                "classes": classes,
                "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
            },
        )
    except Exception as e:
        print("❌ Lỗi khi tải danh sách lớp:", e)
        raise HTTPException(status_code=500, detail="Không thể tải danh sách lớp học.")


@router.get("/students/{class_id}", response_class=HTMLResponse)
def class_students(
    class_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        class_info = class_service.get_teacher_class(db, class_id, current_teacher.id)
        if not class_info:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp học hoặc bạn không có quyền xem.")

        students = class_service.get_students_in_class(db, class_id)

        return render_template(
            request,
            "classes/students.html",
            {
                "class_info": class_info,
                "students": students,
                "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        print("❌ Lỗi khi tải danh sách học viên:", e)
        raise HTTPException(status_code=500, detail="Không thể tải danh sách học viên.")


@router.get("/stats/{class_id}", response_class=HTMLResponse)
def class_statistics(
    class_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        class_info = class_service.get_teacher_class(db, class_id, current_teacher.id)
        if not class_info:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp học hoặc bạn không có quyền xem.")

        stats = class_service.get_class_grade_statistics(db, class_id)

        chart_labels = [row["full_name"] for row in stats]
        chart_quiz = [row["quiz_avg"] for row in stats]
        chart_assign = [row["assignment_avg"] for row in stats]
        chart_total = [row["total_score"] for row in stats]

        return render_template(
            request,
            "classes/statistics.html",
            {
                "class_info": class_info,
                "stats": stats,
                "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
                "chart_labels": chart_labels,
                "chart_quiz": chart_quiz,
                "chart_assign": chart_assign,
                "chart_total": chart_total,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        print("❌ Lỗi khi thống kê điểm lớp:", e)
        raise HTTPException(status_code=500, detail="Không thể thống kê điểm lớp học.")