from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.models.lesson_progress import LessonProgress
from app.models.quiz_attempt import QuizAttempt
from app.models.assignment_submission import AssignmentSubmission
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.services.common.password_service import change_user_password  # ✅ Đổi mật khẩu dùng service chung
import uuid, shutil, os
from datetime import datetime

# ==========================================================
# 🧭 Cấu hình template
# ==========================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ==========================================================
# 🚀 Router
# ==========================================================
router = APIRouter(
    prefix="/student/profile",
    tags=["Student - Profile"]
)

# ==========================================================
# 📄 1️⃣ Trang hồ sơ học viên
# ==========================================================
@router.get("/", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    major = db.query(Major).filter(Major.id == user.major_id).first() if user.major_id else None
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == user.academic_year_id).first() if user.academic_year_id else None

    total_lessons = db.query(LessonProgress).filter(LessonProgress.user_id == user_id).count()
    completed_lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == user_id,
        LessonProgress.progress_status == "completed"
    ).count()

    total_quizzes = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).count()
    total_assignments = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.student_id == user_id
    ).count()

    progress_percent = int((completed_lessons / total_lessons * 100) if total_lessons > 0 else 0)

    return templates.TemplateResponse(
        "student/profile/profile.html",
        {
            "request": request,
            "user": user,
            "major": major,
            "academic_year": academic_year,
            "progress_percent": progress_percent,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_quizzes": total_quizzes,
            "total_assignments": total_assignments,
        },
    )

# ==========================================================
# 🖼️ 2️⃣ Upload nhiều ảnh (jpg, png, jpeg, webp, gif)
# ==========================================================
@router.post("/upload-avatar")
async def upload_avatar(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload 1 hoặc nhiều ảnh đại diện (jpg/png/jpeg/webp/gif)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir = os.path.join(base_dir, "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    allowed_ext = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    avatar_urls = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            continue

        file_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avatar_urls.append(f"/uploads/avatars/{file_name}")

    if avatar_urls:
        user = db.query(User).filter(User.id == user_id).first()
        user.avatar_url = avatar_urls[-1]
        db.commit()

    return RedirectResponse(url="/student/profile", status_code=303)

# ==========================================================
# 🔐 3️⃣ Trang đổi mật khẩu (GET)
# ==========================================================
@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("student/profile/change_password.html", {"request": request})

# ==========================================================
# 💾 4️⃣ Xử lý đổi mật khẩu (POST)
# ==========================================================
@router.post("/change-password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = change_user_password(
        db=db,
        user_id=user_id,
        current_password=current_password,
        new_password=new_password,
        confirm_password=confirm_password
    )

    if not result["success"]:
        return templates.TemplateResponse(
            "student/profile/change_password.html",
            {"request": request, "error": result["message"]},
            status_code=400
        )

    # ✅ Nếu đổi thành công → tự logout
    print(f"✅ Student {user_id} đã đổi mật khẩu thành công. Tự động đăng xuất.")
    request.session.clear()
    return RedirectResponse(url="/auth/login?msg=logout_after_change", status_code=303)
