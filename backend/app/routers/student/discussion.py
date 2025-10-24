from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import discussion_service

router = APIRouter(prefix="/student/discussion", tags=["Student - Discussion"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_discussions(request: Request):
    topics = await discussion_service.get_all_topics()
    return templates.TemplateResponse("student/discussion/list.html", {"request": request, "topics": topics})
