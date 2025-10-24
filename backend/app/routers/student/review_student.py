from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import review_service

router = APIRouter(prefix="/student/review", tags=["Student - Review"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_reviews(request: Request, course_id: str):
    reviews = await review_service.get_reviews_by_course(course_id)
    return templates.TemplateResponse("student/review/review_list.html", {"request": request, "reviews": reviews})
