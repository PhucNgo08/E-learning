from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import notification_service

router = APIRouter(prefix="/student/notifications", tags=["Student - Notifications"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_notifications(request: Request):
    notifications = await notification_service.get_student_notifications()
    return templates.TemplateResponse("student/notifications.html", {"request": request, "notifications": notifications})
