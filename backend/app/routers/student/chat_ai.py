import os
import traceback
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import google.generativeai as genai

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
# 🌐 TRANG GIAO DIỆN - Gợi ý câu hỏi theo ngành
# =====================================================
@router.get("/")
async def chat_ai_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    """Hiển thị giao diện chat AI + lịch sử trò chuyện + gợi ý theo ngành."""
    history = ai_chat_service.get_chat_history(db, current_user.id)

    # 🧩 Lấy thông tin ngành học
    major = db.query(Major).filter(Major.id == current_user.major_id).first()
    major_name = major.major_name if major else "Chưa xác định"

    # 🎓 Gợi ý câu hỏi theo ngành học
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
        (k for k in major_suggestions if k in major_name.lower()), "chưa xác định"
    )
    icon = major_suggestions[selected_major]["icon"]
    suggestions = major_suggestions[selected_major]["suggestions"]

    print(f"🎓 [ChatAI] Ngành: {major_name} → {len(suggestions)} gợi ý")

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
    """Xử lý câu hỏi từ học viên (từ DB hoặc Gemini)."""
    try:
        print(f"🧠 [ChatAI] Tin nhắn nhận được: {message}")
        msg_lower = message.lower()

        course_keywords = ["khóa học", "course", "môn học", "lớp học", "học phần"]
        category_keywords = ["danh mục", "chuyên mục", "category", "lĩnh vực học"]

        # ✅ Lưu tin nhắn của học viên
        ai_chat_service.save_chat_history(
            db, current_user.id, message, None, role="user", source="user_input"
        )

        # 🧩 1️⃣ Câu hỏi về khóa học
        if any(kw in msg_lower for kw in course_keywords):
            print("✅ [ChatAI] Truy vấn khóa học từ DB...")
            courses = db.query(Course).filter(Course.status == "published").limit(10).all()
            if not courses:
                reply = "📚 Hiện chưa có khóa học nào được xuất bản."
            else:
                reply = "📘 Các khóa học hiện có:\n\n"
                for c in courses:
                    reply += f"• {c.course_name} ({c.course_code}) — {c.description or 'Không có mô tả.'}\n"

            # ✅ Lưu phản hồi từ hệ thống (assistant)
            ai_chat_service.save_chat_history(
                db, current_user.id, message, reply, role="assistant", source="database"
            )
            return JSONResponse({"reply": reply})

        # 🧩 2️⃣ Câu hỏi về danh mục khóa học
        if any(kw in msg_lower for kw in category_keywords):
            print("✅ [ChatAI] Truy vấn danh mục khóa học từ DB...")
            categories = db.query(CourseCategory).order_by(CourseCategory.category_name).all()
            if not categories:
                reply = "📂 Hiện chưa có danh mục khóa học nào trong hệ thống."
            else:
                reply = "📂 Các danh mục khóa học có sẵn:\n\n"
                for cat in categories:
                    reply += f"- {cat.category_name}: {cat.description or ''}\n"

            ai_chat_service.save_chat_history(
                db, current_user.id, message, reply, role="assistant", source="database"
            )
            return JSONResponse({"reply": reply})

        # 🤖 3️⃣ Nếu không phải câu hỏi về DB → gọi Gemini AI
        print("🤖 [ChatAI] Không phát hiện từ khóa DB → gọi Gemini API...")
        if not GOOGLE_API_KEY:
            raise ValueError("❌ GOOGLE_API_KEY chưa được cấu hình trong .env")

        model = genai.GenerativeModel("models/gemini-2.5-flash")

        try:
            response = model.generate_content(message)
            reply_text = getattr(response, "text", None)
            if not reply_text:
                reply_text = "⚠️ Gemini không trả lời, vui lòng thử lại."
        except Exception as gemini_err:
            reply_text = f"⚠️ Lỗi khi gọi Gemini API: {gemini_err}"

        print(f"🤖 [Gemini] → {reply_text[:100]}...")
        ai_chat_service.save_chat_history(
            db, current_user.id, message, reply_text, role="assistant", source="gemini"
        )

        return JSONResponse({"reply": reply_text})

    except Exception as e:
        print("💥 [ChatAI ERROR] Lỗi xử lý yêu cầu Chat AI:")
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
    """Xóa toàn bộ lịch sử chat của học viên."""
    try:
        deleted = ai_chat_service.clear_chat_history(db, current_user.id)
        msg = f"🗑️ Đã xóa {deleted} tin nhắn khỏi lịch sử trò chuyện."
        return JSONResponse({"success": True, "message": msg})
    except Exception as e:
        print("💥 [ChatAI ERROR] Lỗi khi xóa lịch sử:")
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
