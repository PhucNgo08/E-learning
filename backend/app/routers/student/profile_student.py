"""
==========================================================
🎓 ROUTER: Student - Profile
Quản lý hồ sơ cá nhân của học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid, shutil, os

# ✅ Database & template
from app.database.connection import get_db
from app.config.template_config import templates

# ✅ Models
from app.models.user import User
from app.models.lesson_progress import LessonProgress
from app.models.quiz_attempt import QuizAttempt
from app.models.assignment_submission import AssignmentSubmission
from app.models.academic_year import AcademicYear
from app.models.major import Major

# ✅ Service đổi mật khẩu
from app.services.common.password_service import change_user_password

# ✅ Upload cấu hình
from app.config.paths import UPLOAD_AVATARS


# =====================================================
# ⚙️ Router
# =====================================================
router = APIRouter(
    prefix="/student/profile",
    tags=["Student - Profile"]
)


# =====================================================
# 📄 1️⃣ Trang hồ sơ học viên
# =====================================================
@router.get("/", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    """Hiển thị trang hồ sơ sinh viên"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # ✅ Đồng bộ avatar vào session
    if not request.session.get("user_avatar") or request.session["user_avatar"] != user.avatar_url:
        request.session["user_avatar"] = user.avatar_url or "/uploads/avatars/default-avatar.png"

    # 🔹 Lấy ngành học & khóa học
    major = db.query(Major).filter(Major.id == user.major_id).first() if user.major_id else None
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == user.academic_year_id).first() if user.academic_year_id else None

    # 📊 Tiến độ học tập
    total_lessons = db.query(LessonProgress).filter(LessonProgress.user_id == user_id).count()
    completed_lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == user_id,
        LessonProgress.progress_status == "completed"
    ).count()
    total_quizzes = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).count()
    total_assignments = db.query(AssignmentSubmission).filter(AssignmentSubmission.student_id == user_id).count()

    progress_percent = int((completed_lessons / total_lessons * 100) if total_lessons > 0 else 0)

    return templates["student"].TemplateResponse(
        "profile/profile.html",
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
            "active_page": "profile",
        },
    )


# =====================================================
# 🖼️ 2️⃣ Upload ảnh đại diện (avatar)
# =====================================================
@router.post("/upload-avatar")
async def upload_avatar(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload và cập nhật ảnh đại diện"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    os.makedirs(UPLOAD_AVATARS, exist_ok=True)
    allowed_ext = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    avatar_urls = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            continue

        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_AVATARS, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avatar_urls.append(f"/uploads/avatars/{filename}")

    if avatar_urls:
        user = db.query(User).filter(User.id == user_id).first()
        new_avatar = avatar_urls[-1]
        user.avatar_url = new_avatar
        user.updated_at = datetime.now()
        db.commit()

        # 🔁 Cập nhật session để sidebar đổi ảnh ngay
        request.session["user_avatar"] = new_avatar
        print(f"🖼️ [Avatar Updated] {user.full_name} → {new_avatar}")

    return RedirectResponse(url="/student/profile", status_code=303)


# =====================================================
# 🔐 3️⃣ Trang đổi mật khẩu (GET)
# =====================================================
@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    """Hiển thị trang đổi mật khẩu"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates["student"].TemplateResponse(
        "profile/change_password.html",
        {"request": request, "active_page": "profile"},
    )


# =====================================================
# 💾 4️⃣ Xử lý đổi mật khẩu (POST)
# =====================================================
@router.post("/change-password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Xử lý đổi mật khẩu & đăng xuất sau khi thành công"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = change_user_password(
        db=db,
        user_id=user_id,
        current_password=current_password,
        new_password=new_password,
        confirm_password=confirm_password,
    )

    if not result["success"]:
        return templates["student"].TemplateResponse(
            "profile/change_password.html",
            {"request": request, "error": result["message"], "active_page": "profile"},
            status_code=400,
        )

    print(f"✅ Student {user_id} đổi mật khẩu thành công — tự động đăng xuất.")
    request.session.clear()
    return RedirectResponse(url="/auth/login?msg=logout_after_change", status_code=303)
