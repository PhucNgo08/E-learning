from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.attempt_answer import AttemptAnswer
from app.models.course import Course
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.user_profile import UserProfile

router = APIRouter(
    prefix="/admin/quiz",
    tags=["Admin - Quiz Management"],
)


VALID_QUIZ_TYPES = {"practice", "graded", "survey"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_STATUSES = {"draft", "pending", "published", "rejected", "archived"}


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "Quản lý Quiz",
        "active_page": "quiz",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def _parse_datetime_local(value: str | None):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.fromisoformat(value)


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _get_quiz_or_404(db: Session, quiz_id: str) -> Quiz:
    quiz = (
        db.query(Quiz)
        .options(
            joinedload(Quiz.course).joinedload(Course.teacher),
            joinedload(Quiz.questions).joinedload(Question.options),
        )
        .filter(Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz")
    return quiz


def _refresh_total_questions(db: Session, quiz_id: str):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz:
        quiz.total_questions = db.query(Question).filter(Question.quiz_id == quiz_id).count()
        quiz.updated_at = datetime.utcnow()
        db.flush()


def _validate_quiz_payload(title, quiz_type, difficulty_level, status, passing_score, max_attempts):
    if not _clean(title):
        raise HTTPException(status_code=400, detail="Tiêu đề quiz không được để trống.")
    if quiz_type not in VALID_QUIZ_TYPES:
        raise HTTPException(status_code=400, detail="Loại quiz không hợp lệ.")
    if difficulty_level not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="Độ khó không hợp lệ.")
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái không hợp lệ.")
    if passing_score < 0 or passing_score > 100:
        raise HTTPException(status_code=400, detail="Điểm đạt phải từ 0 đến 100.")
    if max_attempts <= 0:
        raise HTTPException(status_code=400, detail="Số lần làm phải lớn hơn 0.")


@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/admin/quiz/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def quiz_list(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quizzes = (
        db.query(Quiz)
        .options(joinedload(Quiz.course).joinedload(Course.teacher))
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return render_template(request, "quiz/list.html", {"quizzes": quizzes})


@router.get("/create", response_class=HTMLResponse)
def create_quiz_form(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    courses = db.query(Course).order_by(Course.course_name.asc()).all()
    return render_template(request, "quiz/create.html", {"courses": courses, "form_data": {}})


@router.post("/create", response_class=HTMLResponse)
def create_quiz_submit(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    course_id: str = Form(""),
    quiz_type: str = Form("practice"),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(30),
    max_attempts: int = Form(1),
    passing_score: float = Form(60.0),
    status: str = Form("published"),
    available_from: str = Form(""),
    available_to: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    form_data = dict(
        title=title,
        description=description,
        course_id=course_id,
        quiz_type=quiz_type,
        difficulty_level=difficulty_level,
        time_limit_minutes=time_limit_minutes,
        max_attempts=max_attempts,
        passing_score=passing_score,
        status=status,
        available_from=available_from,
        available_to=available_to,
    )
    try:
        _validate_quiz_payload(title, quiz_type, difficulty_level, status, passing_score, max_attempts)
        course = db.query(Course).filter(Course.id == course_id).first() if course_id else None
        if not course:
            raise HTTPException(status_code=400, detail="Vui lòng chọn khóa học hợp lệ.")

        quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=_clean(description),
            course_id=course_id,
            quiz_type=quiz_type,
            difficulty_level=difficulty_level,
            time_limit_minutes=time_limit_minutes or None,
            max_attempts=max_attempts,
            passing_score=passing_score,
            total_questions=0,
            status=status,
            is_approved=(status == "published"),
            available_from=_parse_datetime_local(available_from),
            available_to=_parse_datetime_local(available_to),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(quiz)
        db.commit()
        return RedirectResponse(f"/admin/quiz/detail/{quiz.id}", status_code=303)
    except HTTPException as e:
        courses = db.query(Course).order_by(Course.course_name.asc()).all()
        return render_template(
            request,
            "quiz/create.html",
            {"courses": courses, "form_data": form_data, "error": e.detail},
            status_code=e.status_code,
        )


@router.get("/detail/{quiz_id}", response_class=HTMLResponse)
def quiz_detail(quiz_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    attempts_count = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).count()
    return render_template(request, "quiz/detail.html", {"quiz": quiz, "attempts_count": attempts_count})


@router.get("/edit/{quiz_id}", response_class=HTMLResponse)
def edit_quiz_form(quiz_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    courses = db.query(Course).order_by(Course.course_name.asc()).all()
    return render_template(request, "quiz/edit.html", {"quiz": quiz, "courses": courses})


@router.post("/edit/{quiz_id}", response_class=HTMLResponse)
def edit_quiz_submit(
    quiz_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    course_id: str = Form(""),
    quiz_type: str = Form("practice"),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(30),
    max_attempts: int = Form(1),
    passing_score: float = Form(60.0),
    status: str = Form("published"),
    available_from: str = Form(""),
    available_to: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    quiz = _get_quiz_or_404(db, quiz_id)
    try:
        _validate_quiz_payload(title, quiz_type, difficulty_level, status, passing_score, max_attempts)
        course = db.query(Course).filter(Course.id == course_id).first() if course_id else None
        if not course:
            raise HTTPException(status_code=400, detail="Vui lòng chọn khóa học hợp lệ.")

        quiz.title = title.strip()
        quiz.description = _clean(description)
        quiz.course_id = course_id
        quiz.quiz_type = quiz_type
        quiz.difficulty_level = difficulty_level
        quiz.time_limit_minutes = time_limit_minutes or None
        quiz.max_attempts = max_attempts
        quiz.passing_score = passing_score
        quiz.status = status
        quiz.is_approved = (status == "published")
        quiz.available_from = _parse_datetime_local(available_from)
        quiz.available_to = _parse_datetime_local(available_to)
        quiz.updated_at = datetime.utcnow()
        db.commit()
        return RedirectResponse(f"/admin/quiz/detail/{quiz_id}", status_code=303)
    except HTTPException as e:
        courses = db.query(Course).order_by(Course.course_name.asc()).all()
        return render_template(
            request,
            "quiz/edit.html",
            {"quiz": quiz, "courses": courses, "error": e.detail},
            status_code=e.status_code,
        )


@router.get("/delete/{quiz_id}", response_class=HTMLResponse)
def confirm_delete_quiz(quiz_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    return render_template(request, "quiz/delete.html", {"quiz": quiz, "page_title": "Xóa Quiz"})


@router.post("/delete/{quiz_id}")
def delete_quiz(quiz_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    db.delete(quiz)
    db.commit()
    return RedirectResponse(url="/admin/quiz/list", status_code=303)


@router.post("/approve/{quiz_id}")
def approve_quiz(quiz_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    quiz.status = "published"
    quiz.is_approved = True
    quiz.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(f"/admin/quiz/detail/{quiz_id}", status_code=303)


@router.post("/reject/{quiz_id}")
def reject_quiz(quiz_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    quiz.status = "rejected"
    quiz.is_approved = False
    quiz.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(f"/admin/quiz/detail/{quiz_id}", status_code=303)


@router.get("/{quiz_id}/question/create", response_class=HTMLResponse)
def create_question_form(quiz_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    return render_template(request, "quiz/question_create.html", {"quiz": quiz})


@router.post("/{quiz_id}/question/create")
def create_question_submit(
    quiz_id: str,
    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...),
    explanation: str = Form(""),
    points: float = Form(1.0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    _get_quiz_or_404(db, quiz_id)
    if correct not in {"a", "b", "c", "d"}:
        raise HTTPException(status_code=400, detail="Đáp án đúng không hợp lệ.")

    question = Question(
        id=str(uuid.uuid4()),
        quiz_id=quiz_id,
        question_type="multiple_choice",
        question_text=question_text.strip(),
        explanation=_clean(explanation),
        points=points,
        difficulty_level="medium",
        question_order=db.query(Question).filter(Question.quiz_id == quiz_id).count() + 1,
    )
    db.add(question)
    db.flush()

    options = {"a": option_a, "b": option_b, "c": option_c, "d": option_d}
    for idx, (key, value) in enumerate(options.items(), start=1):
        db.add(
            QuestionOption(
                id=str(uuid.uuid4()),
                question_id=question.id,
                option_text=value.strip(),
                is_correct=1 if key == correct else 0,
                option_order=idx,
            )
        )

    _refresh_total_questions(db, quiz_id)
    db.commit()
    return RedirectResponse(f"/admin/quiz/detail/{quiz_id}", status_code=303)


@router.post("/question/delete/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    quiz_id = question.quiz_id
    db.delete(question)
    _refresh_total_questions(db, quiz_id)
    db.commit()
    return RedirectResponse(f"/admin/quiz/detail/{quiz_id}", status_code=303)


@router.get("/attempts/{quiz_id}", response_class=HTMLResponse)
def quiz_attempts(quiz_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    quiz = _get_quiz_or_404(db, quiz_id)
    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.user).joinedload(User.profile))
        .filter(QuizAttempt.quiz_id == quiz_id)
        .order_by(QuizAttempt.submitted_at.desc().nullslast(), QuizAttempt.started_at.desc())
        .all()
    )
    return render_template(request, "quiz/attempts.html", {"quiz": quiz, "attempts": attempts})


@router.get("/attempt/{attempt_id}", response_class=HTMLResponse)
def quiz_attempt_detail(attempt_id: str, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    attempt = (
        db.query(QuizAttempt)
        .options(
            joinedload(QuizAttempt.quiz),
            joinedload(QuizAttempt.user).joinedload(User.profile),
            joinedload(QuizAttempt.answers).joinedload(AttemptAnswer.question).joinedload(Question.options),
        )
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài làm.")
    return render_template(request, "quiz/attempt_detail.html", {"attempt": attempt})


@router.post("/attempt/delete/{attempt_id}")
def delete_attempt(attempt_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài làm.")
    quiz_id = attempt.quiz_id
    db.delete(attempt)
    db.commit()
    return RedirectResponse(f"/admin/quiz/attempts/{quiz_id}", status_code=303)
