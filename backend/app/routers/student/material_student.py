from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.student import material_service

router = APIRouter(prefix="/student/material", tags=["Student - Materials"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_materials(request: Request, course_id: str):
    materials = await material_service.get_materials_by_course(course_id)
    return templates.TemplateResponse("student/materials/list.html", {"request": request, "materials": materials})
