from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import schedule_service

router = APIRouter(prefix="/student/schedule", tags=["Student - Schedule"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def view_schedule(request: Request):
    schedule = await schedule_service.get_student_schedule()
    return templates.TemplateResponse("student/schedule/schedule.html", {"request": request, "schedule": schedule})
