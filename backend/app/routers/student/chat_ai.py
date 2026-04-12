import os
import traceback
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import google.generativeai as genai
from starlette.concurrency import run_in_threadpool

# 🧩 Import hệ thống
from app.database.connection import get_db
from app.services.student import ai_chat_service
from app.dependencies.auth import get_current_student
from app.models.course import Course
from app.models.course_category import CourseCategory
from app.models.major import Major

# =====================================================
# 🤖 ROUTER - Chat AI cho học viên
# =====================================================
router = APIRouter(prefix="/student/chat-ai", tags=["Student - Chat AI"])

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("⚠️ [ChatAI] GOOGLE_API_KEY chưa được cấu hình trong .env!")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("✅ [ChatAI] Đã cấu hình Google Gemini API.")


# =====================================================
# ✅ HÀM LẤY TEXT AN TOÀN TỪ GEMINI RESPONSE
# =====================================================
def extract_gemini_text(resp) -> str:
    """
    Gemini đôi khi không trả resp.text mà nằm trong candidates/content/parts.
    Hàm này đảm bảo lấy được text nếu có.
    """
    # 1) cách phổ biến
    t = getattr(resp, "text", None)
    if t and str(t).strip():
        return str(t).strip()

    # 2) fallback: candidates -> content -> parts
    try:
        candidates = getattr(resp, "candidates", None) or []
        for c in candidates:
            content = getattr(c, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            for p in parts:
                pt = getattr(p, "text", None)
                if pt and str(pt).strip():
                    return str(pt).strip()
    except Exception:
        pass

    # 3) fallback: nếu bị block
    try:
        pf = getattr(resp, "prompt_feedback", None)
        block_reason = getattr(pf, "block_reason", None) if pf else None
        if block_reason:
            return f"⚠️ Câu hỏi có thể bị chặn bởi chính sách an toàn ({block_reason}). Bạn thử diễn đạt lại rõ hơn nhé."
    except Exception:
        pass

    return ""


async def call_gemini(prompt: str) -> str:
    """Gọi Gemini không block FastAPI."""
    if not GOOGLE_API_KEY:
        return "⚠️ Hệ thống chưa cấu hình GOOGLE_API_KEY. Vui lòng báo admin."

    model_name = "models/gemini-2.5-flash"  # nếu lỗi model, đổi sang "models/gemini-1.5-flash"

    def _call():
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt)

    try:
        resp = await run_in_threadpool(_call)
        text = extract_gemini_text(resp)
        return text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi Gemini API: {e}"


# =====================================================
# 🌐 TRANG GIAO DIỆN - Gợi ý câu hỏi theo ngành
# =====================================================
@router.get("/")
async def chat_ai_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    history = ai_chat_service.get_chat_history(db, current_user.id)

    major = db.query(Major).filter(Major.id == current_user.major_id).first()
    major_name = major.major_name if major else "Chưa xác định"

    major_suggestions = {
        "công nghệ thông tin": {
            "icon": "💻",
            "suggestions": [
                "Khóa học lập trình Python nào phù hợp với sinh viên năm 4?",
                "Hướng dẫn thiết kế website bằng HTML, CSS, JavaScript?",
                "Có khóa học trí tuệ nhân tạo (AI) nào đang mở không?",
                "Cách tối ưu hiệu suất ứng dụng web trong FastAPI?",
                "Học SQL hiệu quả và nhanh nhất như thế nào?"
            ]
        },
        "kế toán": {
            "icon": "📊",
            "suggestions": [
                "Khóa học kế toán doanh nghiệp nào đang mở?",
                "Cách ghi sổ kế toán trên phần mềm MISA?",
                "Có khóa học tài chính cá nhân cho sinh viên kế toán không?",
                "Hướng dẫn đọc bảng cân đối kế toán?",
                "Học kế toán thực hành ở đâu uy tín?"
            ]
        },
        "du lịch": {
            "icon": "🗺️",
            "suggestions": [
                "Khóa học hướng dẫn viên du lịch có sẵn không?",
                "Cách thuyết trình hấp dẫn khi dẫn tour?",
                "Khóa học nghiệp vụ khách sạn cho sinh viên du lịch?",
                "Có khóa học marketing du lịch nào không?",
                "Cách xử lý tình huống khó khi hướng dẫn khách nước ngoài?"
            ]
        },
        "thiết kế đồ họa": {
            "icon": "🎨",
            "suggestions": [
                "Khóa học Photoshop hoặc Illustrator nào đang mở?",
                "Cách thiết kế poster sáng tạo cho chiến dịch quảng cáo?",
                "Có khóa học UI/UX Design nào không?",
                "Hướng dẫn phối màu chuyên nghiệp trong thiết kế?",
                "Khóa học dựng video bằng After Effects?"
            ]
        },
        "chưa xác định": {
            "icon": "🎓",
            "suggestions": [
                "Các khóa học nổi bật trong hệ thống?",
                "Khóa học nào đang mở đăng ký?",
                "Cách đăng ký khóa học mới trong hệ thống?"
            ]
        }
    }

    selected_major = next(
        (k for k in major_suggestions if k in (major_name or "").lower()), "chưa xác định"
    )
    icon = major_suggestions[selected_major]["icon"]
    suggestions = major_suggestions[selected_major]["suggestions"]

    return request.app.templates.TemplateResponse(
        "student/chat_ai/chat_ai.html",
        {
            "request": request,
            "history": history,
            "user": current_user,
            "major_name": major_name,
            "icon": icon,
            "suggestions": suggestions
        }
    )


# =====================================================
# 💬 API CHAT - Xử lý hỏi & trả lời
# =====================================================
@router.post("/ask")
async def ask_ai(
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    try:
        msg = (message or "").strip()
        if len(msg) < 2:
            return JSONResponse({"reply": "Bạn nhập rõ hơn giúp mình nhé 🙂"})

        msg_lower = msg.lower()

        course_keywords = ["khóa học", "course", "môn học", "lớp học", "học phần"]
        category_keywords = ["danh mục", "chuyên mục", "category", "lĩnh vực học"]

        # ✅ lưu message user
        ai_chat_service.save_chat_history(
            db, current_user.id, msg, None, role="user", source="user_input"
        )

        # ✅ hỏi về khóa học -> query DB
        if any(kw in msg_lower for kw in course_keywords):
            courses = db.query(Course).filter(Course.status == "published").limit(10).all()

            if not courses:
                reply = "📚 Hiện chưa có khóa học nào được xuất bản."
            else:
                reply = "📘 Các khóa học hiện có:\n\n"
                for c in courses:
                    reply += f"• {c.course_name} ({c.course_code}) — {c.description or 'Không có mô tả.'}\n"

            ai_chat_service.save_chat_history(
                db, current_user.id, msg, reply, role="assistant", source="database"
            )
            return JSONResponse({"reply": reply})

        # ✅ hỏi về danh mục -> query DB
        if any(kw in msg_lower for kw in category_keywords):
            categories = db.query(CourseCategory).order_by(CourseCategory.category_name).all()

            if not categories:
                reply = "📂 Hiện chưa có danh mục khóa học nào trong hệ thống."
            else:
                reply = "📂 Các danh mục khóa học có sẵn:\n\n"
                for cat in categories:
                    reply += f"- {cat.category_name}: {cat.description or ''}\n"

            ai_chat_service.save_chat_history(
                db, current_user.id, msg, reply, role="assistant", source="database"
            )
            return JSONResponse({"reply": reply})

        # ✅ không match DB -> gọi Gemini
        reply_text = await call_gemini(msg)

        # ✅ nếu Gemini trả rỗng -> trả lời hướng dẫn rõ ràng
        if not reply_text.strip():
            reply_text = (
                "🤔 Mình chưa hiểu ý bạn.\n\n"
                "Bạn thử hỏi theo mẫu này nhé:\n"
                "• Bạn muốn tìm khóa học gì?\n"
                "• Bạn đang gặp vấn đề gì trong bài?\n"
                "• Bạn cần mình giải thích phần nào?"
            )

        ai_chat_service.save_chat_history(
            db, current_user.id, msg, reply_text, role="assistant", source="gemini"
        )

        return JSONResponse({"reply": reply_text})

    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


# =====================================================
# 🗑️ XÓA LỊCH SỬ CHAT
# =====================================================
@router.post("/clear")
async def clear_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    try:
        deleted = ai_chat_service.clear_chat_history(db, current_user.id)
        return JSONResponse({"success": True, "message": f"🗑️ Đã xóa {deleted} tin nhắn."})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
