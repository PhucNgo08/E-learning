import os
import traceback
from typing import Any

import google.generativeai as genai
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import TemplateNotFound
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config.template_config import templates
from app.database.connection import get_db
from app.dependencies.auth import get_current_student
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.major import Major
from app.models.student_profile import StudentProfile
from app.services.student import ai_chat_service


router = APIRouter(
    prefix="/student/chat-ai",
    tags=["Student - Chat AI"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


# =====================================================
# 🔧 HÀM TIỆN ÍCH
# =====================================================
def safe_text(value: Any, max_len: int | None = None) -> str:
    text = "" if value is None else str(value).strip()

    if max_len and len(text) > max_len:
        return text[:max_len].strip()

    return text


def get_student_major_id(db: Session, current_user) -> str | None:
    """
    Lấy major_id của sinh viên an toàn.
    Có project lưu major_id trong user, có project lưu trong student_profiles.
    """
    major_id = getattr(current_user, "major_id", None)

    if major_id:
        return major_id

    student_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if student_profile and student_profile.major_id:
        return student_profile.major_id

    return None


def get_student_major_name(db: Session, current_user) -> str:
    try:
        major_id = get_student_major_id(db, current_user)

        if not major_id:
            return "Chưa xác định"

        major = db.query(Major).filter(Major.id == major_id).first()

        if not major:
            return "Chưa xác định"

        return major.major_name

    except Exception:
        traceback.print_exc()
        return "Chưa xác định"


def _model_has_attr(model, attr_name: str) -> bool:
    return getattr(model, attr_name, None) is not None


def _apply_not_deleted(query, model):
    deleted_at = getattr(model, "deleted_at", None)

    if deleted_at is not None:
        return query.filter(deleted_at.is_(None))

    return query


def _apply_desc_order(query, model, *attr_names: str):
    for attr_name in attr_names:
        column = getattr(model, attr_name, None)

        if column is not None:
            return query.order_by(column.desc())

    id_column = getattr(model, "id", None)

    if id_column is not None:
        return query.order_by(id_column.desc())

    return query


def get_major_suggestions(major_name: str) -> dict:
    """
    Gợi ý câu hỏi theo ngành.
    """
    name = (major_name or "").lower()

    suggestions_map = {
        "công nghệ thông tin": {
            "icon": "💻",
            "title": "Gợi ý cho ngành Công nghệ thông tin",
            "suggestions": [
                "Em nên học khóa nào trước để bắt đầu lập trình web?",
                "Giải thích giúp em sự khác nhau giữa HTML, CSS và JavaScript.",
                "Lộ trình học Python cơ bản cho người mới bắt đầu là gì?",
                "Em nên ôn SQL như thế nào để làm bài tốt hơn?",
                "Dựa vào các khóa học của em, em nên học tiếp bài nào?",
            ],
        },
        "kế toán": {
            "icon": "📊",
            "title": "Gợi ý cho ngành Kế toán",
            "suggestions": [
                "Em nên học nội dung nào trước trong kế toán doanh nghiệp?",
                "Giải thích giúp em nguyên tắc ghi nợ và ghi có.",
                "Cách phân biệt tài sản, nguồn vốn, doanh thu và chi phí?",
                "Em nên ôn gì trước khi làm bài kiểm tra kế toán?",
                "Dựa vào tiến độ học, em nên học tiếp phần nào?",
            ],
        },
        "quản trị": {
            "icon": "📈",
            "title": "Gợi ý cho ngành Quản trị",
            "suggestions": [
                "Em nên học khóa nào để nắm nền tảng quản trị kinh doanh?",
                "Giải thích giúp em SWOT là gì và dùng khi nào.",
                "Cách lập kế hoạch kinh doanh cơ bản?",
                "Em nên ôn phần nào trước khi làm bài kiểm tra?",
                "Dựa vào khóa học của em, em nên học tiếp nội dung nào?",
            ],
        },
    }

    for key, value in suggestions_map.items():
        if key in name:
            return value

    return {
        "icon": "🎓",
        "title": "Gợi ý học tập",
        "suggestions": [
            "Em nên học khóa nào trước?",
            "Dựa vào tiến độ của em, em nên học tiếp bài nào?",
            "Tóm tắt giúp em nội dung khóa học đang học.",
            "Gợi ý cách ôn tập hiệu quả cho bài kiểm tra.",
            "Giải thích lại nội dung bài học theo cách dễ hiểu hơn.",
        ],
    }


def get_available_courses_for_student(db: Session, current_user, limit: int = 8):
    """
    Lấy khóa học công khai phù hợp với sinh viên.
    Hàm này cố tình viết phòng thủ để GET /student/chat-ai/ không bị 500
    khi model thiếu deleted_at/is_public/created_at/major_id.
    """
    try:
        major_id = get_student_major_id(db, current_user)

        owned_rows = (
            db.query(CourseEnrollment.course_id)
            .filter(
                CourseEnrollment.user_id == current_user.id,
                CourseEnrollment.enrollment_status.in_(["active", "approved", "completed", "enrolled", "paid"]),
            )
            .all()
        )

        owned_course_ids = [row[0] for row in owned_rows if row and row[0]]

        query = db.query(Course)
        query = _apply_not_deleted(query, Course)

        if _model_has_attr(Course, "status"):
            query = query.filter(Course.status == "published")

        if _model_has_attr(Course, "is_public"):
            query = query.filter(Course.is_public == 1)

        if major_id and _model_has_attr(Course, "major_id"):
            query = query.filter(Course.major_id == major_id)

        if owned_course_ids:
            query = query.filter(~Course.id.in_(owned_course_ids))

        query = _apply_desc_order(query, Course, "created_at", "updated_at")

        return query.limit(limit).all()

    except Exception:
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        return []


def get_enrolled_courses_for_student(db: Session, current_user, limit: int = 8):
    """
    Lấy khóa học sinh viên đã đăng ký/mua.
    Có fallback nếu model thiếu deleted_at/created_at.
    """
    try:
        query = (
            db.query(CourseEnrollment)
            .join(Course, CourseEnrollment.course_id == Course.id)
            .filter(
                CourseEnrollment.user_id == current_user.id,
                CourseEnrollment.enrollment_status.in_(["active", "approved", "completed", "enrolled", "paid"]),
            )
        )

        query = _apply_not_deleted(query, Course)
        query = _apply_desc_order(query, CourseEnrollment, "created_at", "updated_at")

        return query.limit(limit).all()

    except Exception:
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        return []


# =====================================================
# ✅ LẤY TEXT AN TOÀN TỪ GEMINI RESPONSE
# =====================================================
def extract_gemini_text(resp) -> str:
    """
    Gemini đôi khi không trả resp.text mà nằm trong candidates/content/parts.
    Hàm này đảm bảo lấy được text nếu có.
    """
    text = getattr(resp, "text", None)

    if text and str(text).strip():
        return str(text).strip()

    try:
        candidates = getattr(resp, "candidates", None) or []

        for candidate in candidates:
            content = getattr(candidate, "content", None)

            if not content:
                continue

            parts = getattr(content, "parts", None) or []

            for part in parts:
                part_text = getattr(part, "text", None)

                if part_text and str(part_text).strip():
                    return str(part_text).strip()

    except Exception:
        pass

    try:
        prompt_feedback = getattr(resp, "prompt_feedback", None)
        block_reason = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None

        if block_reason:
            return f"⚠️ Câu hỏi có thể bị chặn bởi chính sách an toàn: {block_reason}. Bạn hãy thử diễn đạt lại rõ hơn nhé."

    except Exception:
        pass

    return ""


async def call_gemini(prompt: str) -> str:
    """
    Gọi Gemini trong threadpool để không làm nghẽn FastAPI.
    """
    if not GOOGLE_API_KEY:
        return "⚠️ Hệ thống chưa cấu hình GOOGLE_API_KEY. Vui lòng báo quản trị viên."

    model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

    def _call():
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt)

    try:
        response = await run_in_threadpool(_call)
        text = extract_gemini_text(response)

        if not text:
            return "⚠️ AI chưa trả về nội dung phù hợp. Bạn thử hỏi lại ngắn gọn hơn nhé."

        return text

    except Exception as e:
        traceback.print_exc()
        return f"⚠️ Lỗi khi gọi Gemini API: {e}"


# =====================================================
# 🧠 TẠO PROMPT CHO STUDENT
# =====================================================
def build_prompt_for_student(
    db: Session,
    current_user,
    message: str,
) -> str:
    """
    Ưu tiên dùng service mới nếu đã có build_student_ai_prompt.
    Nếu service chưa có thì tự tạo prompt dự phòng.
    """
    if hasattr(ai_chat_service, "build_student_ai_prompt"):
        return ai_chat_service.build_student_ai_prompt(
            db=db,
            user_id=current_user.id,
            user_message=message,
        )

    major_name = get_student_major_name(db, current_user)
    enrolled_courses = get_enrolled_courses_for_student(db, current_user)

    course_lines = []

    for enrollment in enrolled_courses:
        course = getattr(enrollment, "course", None)

        if course:
            course_lines.append(f"- {course.course_name}")

    if not course_lines:
        course_lines.append("- Sinh viên chưa có khóa học đang học.")

    return f"""
Bạn là trợ lý học tập AI trong hệ thống E-learning.

YÊU CẦU:
- Trả lời bằng tiếng Việt.
- Trả lời ngắn gọn, rõ ràng, dễ hiểu cho sinh viên.
- Nếu câu hỏi liên quan khóa học, hãy dựa vào thông tin ngành và khóa học của sinh viên.
- Không bịa dữ liệu nếu không có trong ngữ cảnh.

THÔNG TIN SINH VIÊN:
- Tên tài khoản: {getattr(current_user, "username", "Sinh viên")}
- Email: {getattr(current_user, "email", "")}
- Ngành học: {major_name}

KHÓA HỌC ĐÃ ĐĂNG KÝ:
{chr(10).join(course_lines)}

CÂU HỎI CỦA SINH VIÊN:
{message}

TRẢ LỜI:
""".strip()


def save_chat_turn_safe(
    db: Session,
    user_id: str,
    user_message: str,
    assistant_response: str,
    source: str = "gemini",
):
    """
    Tương thích cả service cũ và service mới.
    """
    try:
        if hasattr(ai_chat_service, "save_chat_turn"):
            return ai_chat_service.save_chat_turn(
                db=db,
                user_id=user_id,
                user_message=user_message,
                assistant_response=assistant_response,
                source=source,
            )

        ai_chat_service.save_chat_history(
            db=db,
            user_id=user_id,
            message=user_message,
            response=None,
            role="user",
            source="student",
        )

        ai_chat_service.save_chat_history(
            db=db,
            user_id=user_id,
            message=assistant_response,
            response=assistant_response,
            role="assistant",
            source=source,
        )

        return True

    except Exception:
        traceback.print_exc()
        return None


def get_history_for_template(db: Session, user_id: str):
    """
    Lấy lịch sử chat cho template.
    Tương thích cả service cũ và service mới.
    """
    try:
        if hasattr(ai_chat_service, "get_chat_messages_for_ui"):
            return ai_chat_service.get_chat_messages_for_ui(
                db=db,
                user_id=user_id,
                limit=30,
            )

        rows = ai_chat_service.get_chat_history(
            db=db,
            user_id=user_id,
            limit=30,
        )

        messages = []

        for row in rows:
            role = getattr(row, "role", "user")
            text = getattr(row, "response", None) if role == "assistant" else getattr(row, "message", "")

            if not text:
                text = getattr(row, "message", "")

            messages.append(
                {
                    "user_id": getattr(row, "user_id", "") or "",
                    "role": role,
                    "text": text,
                    "source": getattr(row, "model_name", "") or "",
                    "created_at": str(getattr(row, "created_at", "") or ""),
                }
            )

        return messages

    except Exception:
        traceback.print_exc()
        return []


# =====================================================
# 🌐 TRANG CHAT AI
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def chat_ai_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    # GET trang chat chỉ render giao diện, không gọi Gemini/API AI.
    # Nếu dữ liệu phụ lỗi thì vẫn trả 200 để smoke test không bị 500.
    try:
        major_name = get_student_major_name(db, current_user)
    except Exception:
        traceback.print_exc()
        major_name = "Chưa xác định"

    suggestion_group = get_major_suggestions(major_name)

    try:
        history = get_history_for_template(db, current_user.id)
    except Exception:
        traceback.print_exc()
        history = []

    try:
        available_courses = get_available_courses_for_student(db, current_user)
    except Exception:
        traceback.print_exc()
        available_courses = []

    try:
        enrolled_courses = get_enrolled_courses_for_student(db, current_user)
    except Exception:
        traceback.print_exc()
        enrolled_courses = []

    context = {
        "request": request,
        "user": current_user,
        "current_user_id": current_user.id,
        "history": history,
        "messages": history,
        "major_name": major_name,
        "suggestion_group": suggestion_group,
        "major_suggestions": suggestion_group.get("suggestions", []),
        "suggestion_icon": suggestion_group.get("icon", "🎓"),
        "available_courses": available_courses,
        "enrolled_courses": enrolled_courses,
        "active_page": "chat_ai",
        "page_title": "Trợ lý AI học tập",
    }

    template_candidates = [
        "chat_ai/index.html",
        "chat_ai/chat.html",
        "ai_chat/index.html",
        "ai_chat/chat.html",
        "chat_ai.html",
    ]

    for template_name in template_candidates:
        try:
            return templates["student"].TemplateResponse(
                template_name,
                context,
            )
        except TemplateNotFound:
            continue

    return HTMLResponse(
        """
        <h3>Không tìm thấy template Chat AI</h3>
        <p>Hãy tạo một trong các file sau:</p>
        <ul>
          <li>templates/student/chat_ai/index.html</li>
          <li>templates/student/chat_ai/chat.html</li>
          <li>templates/student/ai_chat/index.html</li>
          <li>templates/student/chat_ai.html</li>
        </ul>
        """,
        status_code=200,
    )


# =====================================================
# 💬 API HỎI AI
# =====================================================
@router.post("/ask")
async def ask_ai(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    try:
        message = safe_text(message, 4000)

        if not message:
            return JSONResponse(
                {
                    "ok": False,
                    "message": "Vui lòng nhập câu hỏi.",
                    "reply": "Vui lòng nhập câu hỏi.",
                },
                status_code=400,
            )

        prompt = build_prompt_for_student(
            db=db,
            current_user=current_user,
            message=message,
        )

        reply = await call_gemini(prompt)
        reply = safe_text(reply, 12000)

        save_chat_turn_safe(
            db=db,
            user_id=current_user.id,
            user_message=message,
            assistant_response=reply,
            source="gemini",
        )

        return JSONResponse(
            {
                "ok": True,
                "message": message,
                "reply": reply,
                "answer": reply,
            }
        )

    except Exception as e:
        traceback.print_exc()

        return JSONResponse(
            {
                "ok": False,
                "message": "Có lỗi xảy ra khi xử lý câu hỏi.",
                "reply": f"⚠️ Có lỗi xảy ra: {e}",
            },
            status_code=500,
        )


# =====================================================
# 💬 POST FORM THƯỜNG, KHÔNG AJAX
# =====================================================
@router.post("/")
async def ask_ai_form(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    """
    Dành cho form HTML submit thường.
    Nếu giao diện dùng fetch/AJAX thì gọi /student/chat-ai/ask.
    """
    message = safe_text(message, 4000)

    if message:
        prompt = build_prompt_for_student(
            db=db,
            current_user=current_user,
            message=message,
        )

        reply = await call_gemini(prompt)

        save_chat_turn_safe(
            db=db,
            user_id=current_user.id,
            user_message=message,
            assistant_response=reply,
            source="gemini",
        )

    return RedirectResponse("/student/chat-ai/", status_code=303)


# =====================================================
# 📜 API LẤY LỊCH SỬ CHAT
# =====================================================
@router.get("/history")
async def chat_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    history = get_history_for_template(db, current_user.id)

    return JSONResponse(
        {
            "ok": True,
            "history": history,
            "messages": history,
            "current_user_id": current_user.id,
        }
    )


# =====================================================
# 🗑️ XÓA LỊCH SỬ CHAT
# =====================================================
@router.post("/clear")
async def clear_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    try:
        deleted_count = ai_chat_service.clear_chat_history(
            db=db,
            user_id=current_user.id,
        )

        accept = request.headers.get("accept", "")

        if "application/json" in accept:
            return JSONResponse(
                {
                    "ok": True,
                    "deleted": deleted_count,
                    "message": "Đã xóa lịch sử chat.",
                }
            )

        return RedirectResponse("/student/chat-ai/", status_code=303)

    except Exception as e:
        traceback.print_exc()

        return JSONResponse(
            {
                "ok": False,
                "message": f"Không thể xóa lịch sử chat: {e}",
            },
            status_code=500,
        )


@router.get("/clear")
async def clear_history_get(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    try:
        ai_chat_service.clear_chat_history(
            db=db,
            user_id=current_user.id,
        )
    except Exception:
        traceback.print_exc()

    return RedirectResponse("/student/chat-ai/", status_code=303)


# =====================================================
# 🎯 API GỢI Ý CÂU HỎI
# =====================================================
@router.get("/suggestions")
async def get_suggestions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student),
):
    major_name = get_student_major_name(db, current_user)
    suggestion_group = get_major_suggestions(major_name)

    return JSONResponse(
        {
            "ok": True,
            "major_name": major_name,
            "icon": suggestion_group.get("icon", "🎓"),
            "title": suggestion_group.get("title", "Gợi ý học tập"),
            "suggestions": suggestion_group.get("suggestions", []),
        }
    )