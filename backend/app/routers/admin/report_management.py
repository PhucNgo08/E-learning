from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.services.admin.report_management_service import get_dashboard_stats, generate_report
from app.config.template_config import get_template_by_path


# ============================================================
# 🚀 Router
# ============================================================
report_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin - Reports"]
)


# ============================================================
# 📊 1️⃣ Tổng quan thống kê
# ============================================================
@report_router.get("/manage", response_class=HTMLResponse)
def manage_reports(request: Request, db: Session = Depends(get_db)):
    """Trang thống kê tổng quan hệ thống"""
    tpl = get_template_by_path(request.url.path)

    try:
        summary = get_dashboard_stats(db)

        return tpl.TemplateResponse(
            "reports/manage_reports.html",
            {
                "request": request,
                "summary": summary,
                "page_title": "📊 Báo cáo thống kê hệ thống"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thống kê: {str(e)}")


# ============================================================
# 📈 2️⃣ Sinh báo cáo chi tiết (Course / Enrollment / Students / Teachers / Quiz)
# ============================================================
@report_router.post("/generate", response_class=HTMLResponse)
def report_generate(
    request: Request,
    report_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """Sinh báo cáo chi tiết theo loại"""
    tpl = get_template_by_path(request.url.path)

    try:
        data = generate_report(report_type, db)

        return tpl.TemplateResponse(
            "reports/report_result.html",
            {
                "request": request,
                "data": data,
                "report_type": report_type,
                "total": len(data),
                "generated_at": datetime.now()
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo báo cáo: {str(e)}")


# ============================================================
# 🗑️ 3️⃣ Xóa báo cáo (Mock)
# ============================================================
@report_router.delete("/delete/{report_id}")
def delete_report(report_id: str):
    """Xóa báo cáo (mô phỏng)"""
    return {"message": f"✅ Đã xóa báo cáo {report_id} (mô phỏng)"}
