from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import assignment_service

router = APIRouter(prefix="/student/assignment", tags=["Student - Assignment"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_assignments(request: Request, course_id: str):
    assignments = await assignment_service.get_assignments_by_course(course_id)
    return templates.TemplateResponse("student/assignment/list.html", {"request": request, "assignments": assignments})
