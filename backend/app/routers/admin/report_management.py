from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.services.admin.report_management_service import (
    get_dashboard_stats,
    generate_report,
)
from app.config.template_config import get_template_by_path
# from app.dependencies.auth import get_current_admin   # nên thêm nếu có auth admin


report_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin - Reports"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@report_router.get("/manage", response_class=HTMLResponse)
def manage_reports(
    request: Request,
    db: Session = Depends(get_db),
    # current_admin=Depends(get_current_admin),   # bật nếu có auth
):
    """Trang thống kê tổng quan hệ thống"""
    try:
        summary = get_dashboard_stats(db)

        return render_template(
            request,
            "reports/manage_reports.html",
            {
                "summary": summary,
                "page_title": "📊 Báo cáo thống kê hệ thống",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thống kê: {str(e)}")


@report_router.post("/generate", response_class=HTMLResponse)
def report_generate(
    request: Request,
    report_type: str = Form(...),
    db: Session = Depends(get_db),
    # current_admin=Depends(get_current_admin),   # bật nếu có auth
):
    """Sinh báo cáo chi tiết theo loại"""
    try:
        report = generate_report(db, report_type)
        data = report.get("data")

        rows = data if isinstance(data, list) else []
        summary_data = data if isinstance(data, dict) else None

        if isinstance(data, list):
            total = len(data)
        elif isinstance(data, dict):
            total = len(data)
        elif data is None:
            total = 0
        else:
            total = 1

        return render_template(
            request,
            "reports/report_result.html",
            {
                "report": report,
                "report_type": report.get("report_type"),
                "rows": rows,
                "summary_data": summary_data,
                "total": total,
                "generated_at": report.get("generated_at"),
                "page_title": "📈 Kết quả báo cáo",
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo báo cáo: {str(e)}")


# Nếu gọi từ form HTML thường thì nên dùng POST thay vì DELETE
@report_router.post("/delete/{report_id}")
def delete_report(report_id: str):
    """Xóa báo cáo (mô phỏng)"""
    return {"message": f"✅ Đã xóa báo cáo {report_id} (mô phỏng)"}