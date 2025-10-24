from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import message_service

router = APIRouter(prefix="/student/messages", tags=["Student - Messages"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_messages(request: Request):
    messages = await message_service.get_student_messages()
    return templates.TemplateResponse("student/messages.html", {"request": request, "messages": messages})
