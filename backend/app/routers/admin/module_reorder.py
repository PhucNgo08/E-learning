from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services import course_service
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

router = APIRouter(
    prefix="/admin/modules",
    tags=["Admin - Module Management"]
)

@router.get("/reorder", response_class=HTMLResponse)
def reorder_modules(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        tpl = get_template_by_path(request.url.path)
        courses = course_service.get_all_courses(
            db=db,
            user_id=current_user.id,
            role="admin",
            search=None,
        )
        return tpl.TemplateResponse(
            "modules/reorder.html",
            {
                "request": request,
                "courses": courses,
                "current_year": datetime.now().year,
                "page_title": "Sắp xếp module",
                "active_page": "modules",
            }
        )
    except Exception as e:
        return HTMLResponse(f"<pre>Lỗi tải trang: {e}</pre>", status_code=500)