import traceback
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.course_progress import CourseProgress
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.admin.review_stats_service import get_review_statistics
from app.services.admin.user_statistics_service import get_user_statistics

try:
    # File service đã fix nằm tại:
    # backend/app/services/admin/learning_progress_stats_service.py
    from app.services.admin.statistics_service import (
        get_learning_progress_overview,
    )
except Exception:
    # Nếu project chưa có file service này thì route vẫn chạy bằng dữ liệu fallback,
    # tránh làm sập toàn bộ trang thống kê.
    get_learning_progress_overview = None


statistics_router = APIRouter(
    prefix="/admin/statistics",
    tags=["Quản trị - Thống kê"],
)

# Giữ thêm biến router để các nơi khác có thể import theo quy ước chung.
router = statistics_router

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def render_template(
    request: Request,
    template_name: str,
    context: dict[str, Any],
    status_code: int = 200,
):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "📊 Bảng thống kê",
        "active_page": "statistics",
        "now": datetime.now(),
    }
    base_context.update(context or {})
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def _count(db: Session, query) -> int:
    try:
        return int(query.scalar() or 0)
    except Exception:
        return 0


def _course_statistics(db: Session) -> dict[str, Any]:
    total_courses = _count(db, db.query(func.count(Course.id)))
    published_courses = _count(
        db,
        db.query(func.count(Course.id)).filter(Course.status == "published"),
    )
    draft_courses = _count(
        db,
        db.query(func.count(Course.id)).filter(Course.status == "draft"),
    )
    archived_courses = _count(
        db,
        db.query(func.count(Course.id)).filter(Course.status == "archived"),
    )

    total_students = _count(
        db,
        db.query(func.count(distinct(CourseEnrollment.user_id))).filter(
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES)
        ),
    )

    total_lessons = _count(db, db.query(func.count(Lesson.id)))
    completed_lessons = _count(
        db,
        db.query(func.count(LessonProgress.id)).filter(
            LessonProgress.progress_status == "completed"
        ),
    )
    avg_progress = db.query(func.avg(CourseProgress.progress_percent)).scalar() or 0

    return {
        "Tổng khóa học": total_courses,
        "Khóa học đã đăng": published_courses,
        "Khóa học bản nháp": draft_courses,
        "Khóa học lưu trữ": archived_courses,
        "Học viên đang học": total_students,
        "Tổng bài học": total_lessons,
        "Bài học đã hoàn thành": completed_lessons,
        "Tiến độ trung bình": f"{round(float(avg_progress), 1)}%",
        "Tổng bài kiểm tra": _count(db, db.query(func.count(Quiz.id))),
        "Tổng bài tập": _count(db, db.query(func.count(Assignment.id))),
    }


def _user_statistics_vietnamese(db: Session) -> dict[str, Any]:
    raw = get_user_statistics(db) or {}
    by_role = raw.get("by_role", {}) or {}
    by_status = raw.get("by_status", {}) or {}

    role_labels = {
        "admin": "Quản trị viên",
        "teacher": "Giảng viên",
        "student": "Sinh viên",
        "teaching_assistant": "Trợ giảng",
    }
    status_labels = {
        "active": "Đang hoạt động",
        "inactive": "Không hoạt động",
        "suspended": "Tạm khóa",
        "pending": "Đang chờ",
    }

    return {
        "Tổng người dùng": raw.get("total_users", 0),
        "Theo vai trò": {
            role_labels.get(str(k).lower(), k): v
            for k, v in by_role.items()
        },
        "Theo trạng thái": {
            status_labels.get(str(k).lower(), k): v
            for k, v in by_status.items()
        },
        "Đăng nhập gần đây": raw.get("recent_login", []),
    }


def _learning_progress_rows(db: Session, course_id: str | None = None) -> list[dict[str, Any]]:
    query = (
        db.query(CourseEnrollment, Course, User, UserProfile, CourseProgress)
        .join(Course, Course.id == CourseEnrollment.course_id)
        .join(User, User.id == CourseEnrollment.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(
            CourseProgress,
            (CourseProgress.course_id == Course.id)
            & (CourseProgress.user_id == User.id),
        )
        .filter(CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .order_by(
            Course.course_code.asc(),
            UserProfile.full_name.asc(),
            User.username.asc(),
        )
    )

    if course_id:
        query = query.filter(Course.id == course_id)

    rows: list[dict[str, Any]] = []

    for enrollment, course, user, profile, saved_progress in query.all():
        total_lessons = _count(
            db,
            db.query(func.count(Lesson.id))
            .join(Module, Module.id == Lesson.module_id)
            .filter(Module.course_id == course.id),
        )
        completed_lessons = _count(
            db,
            db.query(func.count(distinct(LessonProgress.lesson_id)))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .filter(
                Module.course_id == course.id,
                LessonProgress.user_id == user.id,
                LessonProgress.progress_status == "completed",
            ),
        )

        total_assignments = _count(
            db,
            db.query(func.count(Assignment.id)).filter(
                Assignment.course_id == course.id
            ),
        )
        submitted_assignments = _count(
            db,
            db.query(func.count(distinct(AssignmentSubmission.assignment_id)))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(
                Assignment.course_id == course.id,
                AssignmentSubmission.student_id == user.id,
            ),
        )

        total_quizzes = _count(
            db,
            db.query(func.count(Quiz.id)).filter(Quiz.course_id == course.id),
        )
        completed_quizzes = _count(
            db,
            db.query(func.count(distinct(QuizAttempt.quiz_id)))
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .filter(
                Quiz.course_id == course.id,
                QuizAttempt.user_id == user.id,
                QuizAttempt.status.in_(DONE_QUIZ_STATUSES),
            ),
        )

        if saved_progress and saved_progress.progress_percent is not None:
            progress_percent = float(saved_progress.progress_percent)
        else:
            progress_percent = (
                round((completed_lessons / total_lessons) * 100, 2)
                if total_lessons
                else 0.0
            )

        progress_percent = max(0.0, min(100.0, progress_percent))

        rows.append(
            {
                "course_id": course.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "student_id": user.id,
                "student_name": (
                    profile.full_name
                    if profile and profile.full_name
                    else user.username
                ),
                "email": user.email,
                "enrollment_status": enrollment.enrollment_status,
                "progress_percent": progress_percent,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "submitted_assignments": submitted_assignments,
                "total_assignments": total_assignments,
                "completed_quizzes": completed_quizzes,
                "total_quizzes": total_quizzes,
            }
        )

    return rows


def _fallback_learning_progress_overview(
    courses: list[Course],
    rows: list[dict[str, Any]],
    total_students: int,
    avg_progress: float,
) -> dict[str, Any]:
    completed_students = sum(
        1 for row in rows if float(row.get("progress_percent") or 0) >= 100
    )
    in_progress_students = sum(
        1 for row in rows if 0 < float(row.get("progress_percent") or 0) < 100
    )
    not_started_students = sum(
        1 for row in rows if float(row.get("progress_percent") or 0) <= 0
    )

    # Dữ liệu fallback chỉ dùng để tránh lỗi template khi service overview chưa có.
    return {
        "summary": {
            "total_students": total_students,
            "total_teachers": 0,
            "total_courses": len(courses or []),
            "published_courses": sum(
                1 for course in (courses or []) if getattr(course, "status", None) == "published"
            ),
            "total_enrollments": len(rows or []),
            "total_lessons": sum(int(row.get("total_lessons") or 0) for row in rows),
            "completed_lessons": sum(
                int(row.get("completed_lessons") or 0) for row in rows
            ),
            "lesson_completion_rate": avg_progress,
            "total_assignments": sum(
                int(row.get("total_assignments") or 0) for row in rows
            ),
            "total_submissions": sum(
                int(row.get("submitted_assignments") or 0) for row in rows
            ),
            "graded_submissions": 0,
            "assignment_submit_rate": 0,
            "total_quizzes": sum(int(row.get("total_quizzes") or 0) for row in rows),
            "quiz_attempts": sum(
                int(row.get("completed_quizzes") or 0) for row in rows
            ),
            "avg_progress": avg_progress,
            "completed_students": completed_students,
            "in_progress_students": in_progress_students,
            "not_started_students": not_started_students,
            "filtered_students": total_students,
            "selected_total_students": total_students,
        },
        "top_courses": [],
        "top_students": [],
        "inactive_students": [],
    }


def _safe_learning_progress_overview(
    db: Session,
    courses: list[Course],
    rows: list[dict[str, Any]],
    total_students: int,
    avg_progress: float,
) -> dict[str, Any]:
    try:
        if get_learning_progress_overview:
            overview = get_learning_progress_overview(db) or {}
        else:
            overview = {}
    except Exception:
        print("\n⚠️ LỖI SERVICE TỔNG QUAN TIẾN ĐỘ:\n", traceback.format_exc())
        overview = {}

    if not isinstance(overview, dict) or "summary" not in overview:
        overview = _fallback_learning_progress_overview(
            courses=courses,
            rows=rows,
            total_students=total_students,
            avg_progress=avg_progress,
        )

    summary = dict(overview.get("summary") or {})

    completed_students = sum(
        1 for row in rows if float(row.get("progress_percent") or 0) >= 100
    )
    in_progress_students = sum(
        1 for row in rows if 0 < float(row.get("progress_percent") or 0) < 100
    )
    not_started_students = sum(
        1 for row in rows if float(row.get("progress_percent") or 0) <= 0
    )

    # Bổ sung các key mà template learning_progress.html có thể gọi bằng summary.xxx.
    # Không xóa key cũ của service, chỉ thêm key mới để tránh UndefinedError.
    summary.setdefault("system_total_students", summary.get("total_students", 0))
    summary.setdefault("system_total_courses", summary.get("total_courses", len(courses or [])))
    summary["avg_progress"] = avg_progress
    summary["completed_students"] = completed_students
    summary["in_progress_students"] = in_progress_students
    summary["not_started_students"] = not_started_students
    summary["filtered_students"] = total_students
    summary["selected_total_students"] = total_students

    overview["summary"] = summary
    overview.setdefault("top_courses", [])
    overview.setdefault("top_students", [])
    overview.setdefault("inactive_students", [])
    return overview


@statistics_router.get("/dashboard", response_class=HTMLResponse)
def statistics_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        return render_template(
            request,
            "statistics/dashboard.html",
            {
                "user_stats": _user_statistics_vietnamese(db),
                "course_stats": _course_statistics(db),
                "review_stats": get_review_statistics(db),
                "page_title": "📊 Bảng thống kê hệ thống",
            },
        )
    except Exception:
        print("\n❌ LỖI TẢI BẢNG THỐNG KÊ:\n", traceback.format_exc())
        return HTMLResponse(
            f"<pre>{traceback.format_exc()}</pre>",
            status_code=500,
        )


@statistics_router.get("/learning-progress", response_class=HTMLResponse)
def learning_progress(
    request: Request,
    course_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        courses = (
            db.query(Course)
            .order_by(Course.course_code.asc(), Course.course_name.asc())
            .all()
        )
        rows = _learning_progress_rows(db, course_id=course_id)

        total_students = len(rows)
        avg_progress = (
            round(
                sum(float(row.get("progress_percent") or 0) for row in rows)
                / total_students,
                1,
            )
            if total_students
            else 0
        )

        overview = _safe_learning_progress_overview(
            db=db,
            courses=courses,
            rows=rows,
            total_students=total_students,
            avg_progress=avg_progress,
        )

        return render_template(
            request,
            "statistics/learning_progress.html",
            {
                "courses": courses,
                "selected_course_id": course_id,
                "progress_rows": rows,
                "total_students": total_students,
                "avg_progress": avg_progress,
                "summary": overview.get("summary", {}),
                "top_courses": overview.get("top_courses", []),
                "top_students": overview.get("top_students", []),
                "inactive_students": overview.get("inactive_students", []),
                "learning_overview": overview,
                "page_title": "📈 Theo dõi tiến độ học tập",
            },
        )
    except Exception:
        print("\n❌ LỖI TẢI TIẾN ĐỘ HỌC TẬP:\n", traceback.format_exc())
        return HTMLResponse(
            f"<pre>{traceback.format_exc()}</pre>",
            status_code=500,
        )
