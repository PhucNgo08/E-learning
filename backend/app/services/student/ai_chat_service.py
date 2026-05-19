from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.ai_chat_history import AIChatHistory
import uuid
import traceback


VALID_ROLES = {"user", "assistant"}
VALID_SOURCES = {"gemini", "database", "system", "student", "course"}


# ======================================================
# 🔧 Hàm xử lý an toàn
# ======================================================
def _new_id() -> str:
    return str(uuid.uuid4())


def _safe_text(value, max_len: int | None = None) -> str:
    text = "" if value is None else str(value).strip()

    if max_len and len(text) > max_len:
        return text[:max_len].strip()

    return text


def _normalize_role(role: str | None) -> str:
    role = (role or "user").strip().lower()

    if role not in VALID_ROLES:
        role = "user"

    return role


def _normalize_source(source: str | None) -> str:
    source = (source or "gemini").strip().lower()

    if source not in VALID_SOURCES:
        source = "gemini"

    return source


# ======================================================
# 💾 Lưu 1 dòng lịch sử chat
# ======================================================
def save_chat_history(
    db: Session,
    user_id: str,
    message: str,
    response: str | None = None,
    role: str = "user",
    source: str = "gemini",
):
    """
    Lưu một dòng chat vào database.

    role:
    - user
    - assistant

    source:
    - gemini
    - database
    - system
    - student
    - course
    """
    try:
        if not user_id:
            raise ValueError("user_id bị trống, không thể lưu lịch sử chat.")

        role = _normalize_role(role)
        source = _normalize_source(source)

        message = _safe_text(message, 8000)
        response = _safe_text(response, 12000) if response else None

        if not message and not response:
            return None

        history = AIChatHistory(
            id=_new_id(),
            user_id=user_id,
            role=role,
            message=message,
            response=response,
            model_name=source,
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return history

    except Exception as e:
        db.rollback()
        print("💥 [AIChat ERROR] Lỗi khi lưu lịch sử chat:")
        traceback.print_exc()
        print(f"Chi tiết lỗi: {e}")
        return None


# ======================================================
# 💬 Lưu trọn 1 lượt hỏi/đáp
# ======================================================
def save_chat_turn(
    db: Session,
    user_id: str,
    user_message: str,
    assistant_response: str,
    source: str = "gemini",
):
    """
    Lưu 1 lượt hội thoại gồm:
    - 1 dòng user
    - 1 dòng assistant

    Hàm này phù hợp nhất cho giao diện chat student.
    """
    try:
        if not user_id:
            raise ValueError("user_id bị trống, không thể lưu lượt chat.")

        user_message = _safe_text(user_message, 8000)
        assistant_response = _safe_text(assistant_response, 12000)
        source = _normalize_source(source)

        if not user_message:
            return None, None

        user_row = AIChatHistory(
            id=_new_id(),
            user_id=user_id,
            role="user",
            message=user_message,
            response=None,
            model_name="student",
        )

        assistant_row = AIChatHistory(
            id=_new_id(),
            user_id=user_id,
            role="assistant",
            message=assistant_response,
            response=assistant_response,
            model_name=source,
        )

        db.add(user_row)
        db.add(assistant_row)
        db.commit()

        db.refresh(user_row)
        db.refresh(assistant_row)

        return user_row, assistant_row

    except Exception as e:
        db.rollback()
        print("💥 [AIChat ERROR] Lỗi khi lưu lượt hỏi/đáp:")
        traceback.print_exc()
        print(f"Chi tiết lỗi: {e}")
        return None, None


# ======================================================
# 📜 Lấy lịch sử chat
# ======================================================
def get_chat_history(
    db: Session,
    user_id: str,
    limit: int = 30,
    newest_first: bool = False,
):
    """
    Lấy lịch sử chat gần nhất.

    newest_first=False:
    - Trả về theo thứ tự cũ -> mới
    - Phù hợp để hiển thị trong khung chat
    """
    try:
        if not user_id:
            return []

        limit = max(1, min(int(limit or 30), 100))

        query = (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == user_id)
        )

        if newest_first:
            return (
                query.order_by(AIChatHistory.created_at.desc())
                .limit(limit)
                .all()
            )

        rows = (
            query.order_by(AIChatHistory.created_at.desc())
            .limit(limit)
            .all()
        )

        return list(reversed(rows))

    except Exception as e:
        print("⚠️ [AIChat] Không thể lấy lịch sử chat:")
        traceback.print_exc()
        print(f"Chi tiết lỗi: {e}")
        return []


# ======================================================
# 🧩 Lấy lịch sử dạng dễ render cho giao diện
# ======================================================
def get_chat_messages_for_ui(db: Session, user_id: str, limit: int = 30):
    """
    Trả về dạng:

    [
      {"role": "user", "text": "..."},
      {"role": "assistant", "text": "..."}
    ]
    """
    rows = get_chat_history(
        db=db,
        user_id=user_id,
        limit=limit,
        newest_first=False,
    )

    messages = []

    for row in rows:
        role = _normalize_role(getattr(row, "role", "user"))

        if role == "assistant":
            text = getattr(row, "response", None) or getattr(row, "message", "")
        else:
            text = getattr(row, "message", "")

        text = _safe_text(text)

        if text:
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


# ======================================================
# 🎓 Tạo ngữ cảnh học tập cho sinh viên
# ======================================================
def build_student_learning_context(db: Session, user_id: str) -> str:
    """
    Chỉ lấy dữ liệu của đúng học viên đang hỏi AI.
    Không lấy toàn bộ khóa học trong hệ thống.
    """
    try:
        from app.models.user import User
        from app.models.user_profile import UserProfile
        from app.models.student_profile import StudentProfile
        from app.models.major import Major
        from app.models.course import Course
        from app.models.course_enrollment import CourseEnrollment
        from app.models.module import Module
        from app.models.lesson import Lesson
        from app.models.lesson_progress import LessonProgress

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return "Không tìm thấy thông tin sinh viên."

        profile = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

        student_profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == user_id)
            .first()
        )

        full_name = None

        if profile and getattr(profile, "full_name", None):
            full_name = profile.full_name.strip()

        if not full_name:
            full_name = "em"

        major_name = "Chưa cập nhật"

        if student_profile and getattr(student_profile, "major_id", None):
            major = (
                db.query(Major)
                .filter(Major.id == student_profile.major_id)
                .first()
            )

            if major:
                major_name = major.major_name

        # Chỉ lấy khóa học của học viên đang đăng nhập
        enrollments = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.enrollment_status.in_(
                    ["active", "approved", "completed", "enrolled", "paid"]
                ),
            )
            .all()
        )

        course_lines = []

        for enrollment in enrollments:
            course = (
                db.query(Course)
                .filter(
                    Course.id == enrollment.course_id,
                    Course.deleted_at.is_(None),
                )
                .first()
            )

            if not course:
                continue

            total_lessons = (
                db.query(Lesson)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    Module.course_id == course.id,
                    Module.deleted_at.is_(None),
                    Lesson.deleted_at.is_(None),
                )
                .count()
            )

            completed_lessons = (
                db.query(LessonProgress)
                .join(Lesson, LessonProgress.lesson_id == Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    LessonProgress.user_id == user_id,
                    LessonProgress.progress_status == "completed",
                    Module.course_id == course.id,
                    Module.deleted_at.is_(None),
                    Lesson.deleted_at.is_(None),
                )
                .count()
            )

            percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0

            course_lines.append(
                f"- {course.course_name} ({course.course_code or 'Chưa có mã'}): "
                f"{course.description or 'Chưa có mô tả'} | "
                f"Tiến độ: {completed_lessons}/{total_lessons} bài học ({percent}%)"
            )

        if not course_lines:
            course_lines.append("- Sinh viên hiện chưa đăng ký hoặc chưa mua khóa học nào.")

        return (
            "THÔNG TIN RIÊNG CỦA SINH VIÊN ĐANG HỎI:\n"
            f"- Cách gọi sinh viên: {full_name}\n"
            f"- Email: {getattr(user, 'email', '')}\n"
            f"- Ngành học: {major_name}\n"
            "- Khóa học của sinh viên này:\n"
            + "\n".join(course_lines)
        )

    except Exception:
        traceback.print_exc()
        return "Không thể lấy đầy đủ dữ liệu riêng của sinh viên."
    
# ======================================================
# 🧠 Tạo prompt gửi cho AI
# ======================================================
def build_student_ai_prompt(
    db: Session,
    user_id: str,
    user_message: str,
    max_history: int = 8,
) -> str:
    """
    Tạo prompt hoàn chỉnh cho Gemini/AI.
    """
    user_message = _safe_text(user_message, 8000)

    context = build_student_learning_context(db, user_id)

    recent_messages = get_chat_messages_for_ui(
        db=db,
        user_id=user_id,
        limit=max_history,
    )

    history_lines = []

    for item in recent_messages[-max_history:]:
        if item["role"] == "user":
            role_label = "Sinh viên"
        else:
            role_label = "Trợ lý AI"

        history_lines.append(f"{role_label}: {item['text']}")

    history_block = "\n".join(history_lines) if history_lines else "Chưa có lịch sử chat trước đó."

    return f"""
Bạn là trợ lý học tập AI trong hệ thống E-learning.

YÊU CẦU TRẢ LỜI:
- Luôn trả lời bằng tiếng Việt.
- Trả lời ngắn gọn, rõ ràng, dễ hiểu với sinh viên.
- Không gọi sinh viên bằng mã số sinh viên, username hoặc MSSV.
- Nếu không biết họ tên thật, hãy gọi là "em" hoặc "bạn".
- Nếu câu hỏi liên quan đến khóa học, hãy dựa vào danh sách khóa học sinh viên đang học.
- Nếu sinh viên hỏi "khóa học em đang học", hãy ưu tiên khóa học đã đăng ký/mua trong ngữ cảnh.
- Khi tóm tắt khóa học, hãy nêu: nội dung chính, kỹ năng học được và mục tiêu sau khi học.
- Không bịa điểm số, lịch học, bài kiểm tra hoặc dữ liệu không có trong ngữ cảnh.
- Nếu thiếu dữ liệu, hãy nói rõ là hệ thống chưa có đủ thông tin.
- Chỉ trả lời dựa trên dữ liệu của sinh viên đang hỏi trong phần "THÔNG TIN RIÊNG CỦA SINH VIÊN ĐANG HỎI".
- Không liệt kê toàn bộ khóa học hệ thống nếu sinh viên hỏi về khóa học của em.

{context}

LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{history_block}

CÂU HỎI HIỆN TẠI CỦA SINH VIÊN:
{user_message}

TRẢ LỜI:
""".strip()


# ======================================================
# 📊 Thống kê chat
# ======================================================
def get_chat_stats(db: Session, user_id: str) -> dict:
    try:
        total = (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == user_id)
            .count()
        )

        user_messages = (
            db.query(AIChatHistory)
            .filter(
                AIChatHistory.user_id == user_id,
                AIChatHistory.role == "user",
            )
            .count()
        )

        assistant_messages = (
            db.query(AIChatHistory)
            .filter(
                AIChatHistory.user_id == user_id,
                AIChatHistory.role == "assistant",
            )
            .count()
        )

        return {
            "total": total,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
        }

    except Exception:
        traceback.print_exc()
        return {
            "total": 0,
            "user_messages": 0,
            "assistant_messages": 0,
        }


# ======================================================
# 🗑️ Xóa lịch sử chat
# ======================================================
def clear_chat_history(db: Session, user_id: str):
    """Xóa toàn bộ lịch sử chat của học viên."""
    try:
        if not user_id:
            return 0

        deleted_count = (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == user_id)
            .delete()
        )

        db.commit()
        return deleted_count

    except Exception as e:
        db.rollback()
        print("💥 [AIChat ERROR] Lỗi khi xóa lịch sử chat:")
        traceback.print_exc()
        print(f"Chi tiết lỗi: {e}")
        return 0