

from app.models.quiz_template import QuizTemplate

from fastapi import (
    APIRouter, Request, Depends, Form,
    UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
 
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import pandas as pd
import csv
import uuid
import io
import json
import csv
import re
import traceback
# ======================================================
# Dependencies
# ======================================================
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

# ======================================================
# Models
# ======================================================
from app.models.course import Course
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from app.models.user import User

# ======================================================
# Quiz Services
# ======================================================
from app.services.quiz_service_full_v12 import (
    create_quiz,
    update_quiz,
    delete_quiz,

    create_exam,
    update_exam,
    delete_exam,
    get_quiz_statistics,
)

# ======================================================
# Router Init
# ======================================================
router = APIRouter(
    prefix="/teacher/quizzes",
    tags=["Teacher – Quizzes"],
)


# ======================================================
# Helper — Auto load Quiz
# ======================================================
def auto_get_quiz(db: Session, teacher_id: str, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .options(
            joinedload(Quiz.questions).joinedload(Question.options),
            joinedload(Quiz.course)
        )
        .join(Course)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return None, None
    return quiz, quiz.quiz_type


def parse_dt_local(value: str | None):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.fromisoformat(value)


def ensure_import_cache(request: Request):
    if not hasattr(request.app.state, "import_cache"):
        request.app.state.import_cache = {}
    return request.app.state.import_cache


def refresh_total_questions(db: Session, quiz: Quiz):
    quiz.total_questions = db.query(Question).filter(Question.quiz_id == quiz.id).count()
    db.flush()


# ======================================================
# Redirect default
# ======================================================
@router.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/teacher/quizzes/list", 303)


# ======================================================
# 1) LIST QUIZ
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def quiz_list(request: Request, db=Depends(get_db), teacher=Depends(get_current_teacher)):

    quizzes = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == teacher.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/list.html",
        {"request": request, "quizzes": quizzes, "teacher": teacher}
    )


# ======================================================
# 2) CREATE QUIZ PAGE
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, db=Depends(get_db), teacher=Depends(get_current_teacher)):
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quizzes/create.html", {
        "request": request,
        "courses": courses
    })


# ======================================================
# 3) CREATE QUIZ POST
# ======================================================
@router.post("/create")
def create_quiz_post(
    db: Session = Depends(get_db),
    teacher=Depends(get_current_teacher),

    course_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    quiz_type: str = Form(...),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(30),
    max_attempts: int = Form(1),
    passing_score: float = Form(60.0),
    total_questions: int = Form(10),

    available_from: str = Form(""),
    available_to: str = Form(""),
):
    time_limit_minutes = int(time_limit_minutes)
    max_attempts = int(max_attempts)
    total_questions = int(total_questions)
    passing_score = float(passing_score)

    if quiz_type == "graded":
        af = parse_dt_local(available_from) or datetime.utcnow()
        at = parse_dt_local(available_to) or datetime.utcnow().replace(hour=23, minute=59, second=0, microsecond=0)

        create_exam(
            db=db,
            user_id=teacher.id,
            role="teacher",
            title=title,
            description=description,
            course_id=course_id,
            total_questions=total_questions,
            time_limit=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            available_from=af,
            available_to=at,
        )
    else:
        create_quiz(
            db=db,
            teacher_id=teacher.id,
            course_id=course_id,
            title=title,
            description=description,
            quiz_type="practice",
            difficulty_level=difficulty_level,
            time_limit_minutes=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            total_questions=total_questions,
        )

    return RedirectResponse("/teacher/quizzes/list", 303)


# ======================================================
# 4) EDIT PAGE
# ======================================================
@router.get("/edit/{quiz_id}", response_class=HTMLResponse)
def edit_page(quiz_id: str, request: Request,
              db=Depends(get_db), teacher=Depends(get_current_teacher)):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quizzes/edit.html", {
        "request": request,
        "quiz": quiz,
        "courses": courses,
        "mode": mode
    })


# ======================================================
# 5) EDIT POST
# ======================================================
@router.post("/edit/{quiz_id}")
def edit_post(
    quiz_id: str,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),

    course_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    quiz_type: str = Form(...),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(30),
    max_attempts: int = Form(1),
    passing_score: float = Form(60.0),
    total_questions: int = Form(10),

    available_from: str = Form(""),
    available_to: str = Form(""),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    time_limit_minutes = int(time_limit_minutes)
    max_attempts = int(max_attempts)
    total_questions = int(total_questions)
    passing_score = float(passing_score)

    if mode == "graded":
        af = parse_dt_local(available_from) or quiz.available_from
        at = parse_dt_local(available_to) or quiz.available_to

        update_exam(
            db=db,
            user_id=teacher.id,
            role="teacher",
            exam_id=quiz_id,
            title=title,
            description=description,
            total_questions=total_questions,
            time_limit=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            available_from=af,
            available_to=at
        )
    else:
        update_quiz(
            db=db,
            teacher_id=teacher.id,
            quiz_id=quiz_id,
            course_id=course_id,
            title=title,
            description=description,
            quiz_type="practice",
            difficulty_level=difficulty_level,
            time_limit_minutes=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            total_questions=total_questions
        )

    return RedirectResponse("/teacher/quizzes/list", 303)


# ======================================================
# 6) DELETE PAGE
# ======================================================
@router.get("/delete/{quiz_id}", response_class=HTMLResponse)
def delete_page(
    quiz_id: str, request: Request,
    db=Depends(get_db), teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quizzes/delete.html", {
        "request": request,
        "quiz": quiz
    })


# ======================================================
# 7) DELETE POST
# ======================================================
@router.post("/delete/{quiz_id}")
def delete_post(
    quiz_id: str,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    if mode == "graded":
        delete_exam(db, teacher.id, "teacher", quiz_id)
    else:
        delete_quiz(db, teacher.id, quiz_id)

    return RedirectResponse("/teacher/quizzes/list", 303)


# ======================================================
# 8) DETAIL PAGE
# ======================================================
@router.get("/detail/{quiz_id}", response_class=HTMLResponse)
def detail_page(
    quiz_id: str, request: Request,
    db=Depends(get_db), teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quizzes/detail.html", {
        "request": request,
        "quiz": quiz,
        "questions": quiz.questions
    })


# ======================================================
# 8.1) PREVIEW QUIZ — XEM THỬ NHƯ HỌC VIÊN
# ======================================================
@router.get("/preview/{quiz_id}", response_class=HTMLResponse)
def preview_page(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/preview.html",
        {
            "request": request,
            "quiz": quiz,
            "questions": quiz.questions,
            "teacher": teacher,
        },
    )


# ======================================================
# 9) STATISTICS PAGE
# ======================================================
@router.get("/statistics/{quiz_id}", response_class=HTMLResponse)
def statistics_page(quiz_id: str, request: Request,
                    db=Depends(get_db), teacher=Depends(get_current_teacher)):

    data = get_quiz_statistics(db, teacher.id, quiz_id)
    if not data:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quizzes/statistics.html", {
        "request": request,
        "quiz": data["quiz"],
        "stats": data["stats"],
        "top_students": data["top_students"]
    })




# ======================================================
# 9.1) ATTEMPTS PAGE – GIÁO VIÊN XEM BÀI LÀM
# ======================================================
@router.get("/attempts/{quiz_id}", response_class=HTMLResponse)
def attempts_page(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.user).joinedload(User.profile))
        .filter(QuizAttempt.quiz_id == quiz_id)
        .order_by(
            case(
                (QuizAttempt.submitted_at.is_(None), 1),
                else_=0
            ),
            QuizAttempt.submitted_at.desc(),
            QuizAttempt.started_at.desc()
        )
        .all()
    )

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/attempts.html",
        {"request": request, "quiz": quiz, "attempts": attempts},
    )


# ======================================================
# 9.2) ATTEMPT DETAIL – GIÁO VIÊN XEM ĐÚNG/SAI TỪNG CÂU
# ======================================================
@router.get("/attempt/{attempt_id}", response_class=HTMLResponse)
def attempt_detail_page(
    attempt_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    attempt = (
        db.query(QuizAttempt)
        .options(
            joinedload(QuizAttempt.quiz).joinedload(Quiz.course),
            joinedload(QuizAttempt.user).joinedload(User.profile),
            joinedload(QuizAttempt.answers)
            .joinedload(AttemptAnswer.question)
            .joinedload(Question.options),
        )
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )

    if not attempt or not attempt.quiz or not attempt.quiz.course or attempt.quiz.course.teacher_id != teacher.id:
        raise HTTPException(404, "Không tìm thấy bài làm hoặc bạn không có quyền xem.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/attempt_detail.html",
        {"request": request, "attempt": attempt},
    )


# ======================================================
# 10) API – SCORE DISTRIBUTION
# ======================================================
@router.get("/api/{quiz_id}/score-distribution")
def score_distribution_api(
    quiz_id: str,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        return JSONResponse({"counts": [0, 0, 0, 0]})

    attempts = (
        db.query(QuizAttempt.score)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "submitted"
        )
        .all()
    )

    buckets = [0, 0, 0, 0]
    for a in attempts:
        s = a[0] or 0
        if s < 50:
            buckets[0] += 1
        elif s < 70:
            buckets[1] += 1
        elif s < 90:
            buckets[2] += 1
        else:
            buckets[3] += 1

    return JSONResponse({"counts": buckets})


# ======================================================
# 11) IMPORT — HELPERS
# Hỗ trợ cả dạng ngang:
#   Câu hỏi|A|B|C|D|B
# và dạng dọc:
#   Câu hỏi
#   A. ...
#   B. ...
#   C. ...
#   D. ...
#   Đáp án đúng: B
# ======================================================
REQUIRED_COLS = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct"]

HEADER_ALIASES = {
    "question": "question_text",
    "question_text": "question_text",
    "questiontext": "question_text",
    "q": "question_text",
    "noi_dung": "question_text",
    "nội_dung": "question_text",
    "cau_hoi": "question_text",
    "câu_hỏi": "question_text",

    "a": "option_a",
    "pa": "option_a",
    "option_a": "option_a",
    "option1": "option_a",
    "answer_a": "option_a",

    "b": "option_b",
    "pb": "option_b",
    "option_b": "option_b",
    "option2": "option_b",
    "answer_b": "option_b",

    "c": "option_c",
    "pc": "option_c",
    "option_c": "option_c",
    "option3": "option_c",
    "answer_c": "option_c",

    "d": "option_d",
    "pd": "option_d",
    "option_d": "option_d",
    "option4": "option_d",
    "answer_d": "option_d",

    "correct": "correct",
    "answer": "correct",
    "correct_answer": "correct",
    "dap_an": "correct",
    "đáp_án": "correct",
    "dap_an_dung": "correct",
    "đáp_án_đúng": "correct",
}


def detect_delimiter(text: str):
    if "|" in text:
        return "|"
    if "\t" in text:
        return "\t"
    if ";" in text:
        return ";"
    return ","


def normalize_header(value):
    return (
        str(value or "")
        .lower()
        .strip()
        .replace("\ufeff", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def auto_map_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    raw_cols = list(df.columns)

    # File không có header: pandas sẽ đặt tên cột bằng số.
    if all(str(c).isdigit() for c in raw_cols):
        while len(df.columns) < 6:
            df[len(df.columns)] = ""
        df = df.iloc[:, :6]
        df.columns = REQUIRED_COLS
        return df

    normalized = [normalize_header(c) for c in raw_cols]
    mapped = [HEADER_ALIASES.get(c) for c in normalized]

    # Không nhận ra header thì coi 6 cột đầu là dữ liệu.
    if all(m is None for m in mapped):
        while len(df.columns) < 6:
            df[len(df.columns)] = ""
        df = df.iloc[:, :6]
        df.columns = REQUIRED_COLS
        return df

    final_cols = []
    for i, col in enumerate(mapped):
        final_cols.append(col or f"col_{i}")

    df.columns = final_cols

    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""

    return df[REQUIRED_COLS]


def normalize_import_value(v):
    if v is None:
        return ""
    try:
        if isinstance(v, float) and pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).replace("\ufeff", "").strip()


def normalize_correct_answer(value):
    value = normalize_import_value(value).lower()

    mapping = {
        "a": "a", "1": "a", "option_a": "a", "đáp án a": "a", "dap an a": "a",
        "b": "b", "2": "b", "option_b": "b", "đáp án b": "b", "dap an b": "b",
        "c": "c", "3": "c", "option_c": "c", "đáp án c": "c", "dap an c": "c",
        "d": "d", "4": "d", "option_d": "d", "đáp án d": "d", "dap an d": "d",
    }

    return mapping.get(value, value)


def make_import_row(question_text, option_a, option_b, option_c, option_d, correct, row_number=None):
    question_text = normalize_import_value(question_text)
    option_a = normalize_import_value(option_a)
    option_b = normalize_import_value(option_b)
    option_c = normalize_import_value(option_c)
    option_d = normalize_import_value(option_d)
    correct_raw = normalize_import_value(correct)
    correct_norm = normalize_correct_answer(correct_raw)

    options_by_key = {
        "a": option_a,
        "b": option_b,
        "c": option_c,
        "d": option_d,
    }

    errors = []
    if not question_text:
        errors.append("Thiếu câu hỏi")
    if not option_a:
        errors.append("Thiếu đáp án A")
    if not option_b:
        errors.append("Thiếu đáp án B")
    if not option_c:
        errors.append("Thiếu đáp án C")
    if not option_d:
        errors.append("Thiếu đáp án D")

    valid_correct_values = {"a", "b", "c", "d"}
    valid_correct_values.update(v.lower() for v in options_by_key.values() if v)

    if correct_norm not in valid_correct_values:
        errors.append("Đáp án đúng không hợp lệ")

    if correct_norm not in {"a", "b", "c", "d"}:
        for key, val in options_by_key.items():
            if val and correct_norm == val.lower():
                correct_norm = key
                break

    return {
        "row_number": row_number,
        "question_text": question_text,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct": correct_norm,
        "correct_raw": correct_raw,
        "is_valid": len(errors) == 0,
        "error": "; ".join(errors) if errors else "Hợp lệ",
    }


def parse_option_line(line: str):
    line = normalize_import_value(line)
    match = re.match(r"^([A-Da-d])[\.\)\:\-]\s*(.+)$", line)
    if not match:
        return None
    return match.group(1).lower(), normalize_import_value(match.group(2))


def parse_correct_line(line: str):
    line = normalize_import_value(line)
    match = re.search(
        r"(đáp\s*án\s*(đúng)?|dap\s*an\s*(dung)?|correct\s*answer|answer)\s*[:：\-]?\s*([A-Da-d1-4])",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return normalize_correct_answer(match.group(4))


def parse_horizontal_line(line: str, row_number=None):
    line = normalize_import_value(line)
    if not line:
        return None

    delimiter = detect_delimiter(line)
    # Không cố đọc dòng dạng dọc.
    if delimiter == "," and line.count(",") < 5:
        return None
    if delimiter != "," and delimiter not in line:
        return None

    try:
        reader = csv.reader(io.StringIO(line), delimiter=delimiter)
        cols = next(reader)
    except Exception:
        return None

    cols = [normalize_import_value(c) for c in cols]
    if len(cols) < 6:
        return None

    first = " ".join(cols[:2]).lower()
    if "question" in first or "câu hỏi" in first or "cau hoi" in first:
        return None

    return make_import_row(cols[0], cols[1], cols[2], cols[3], cols[4], cols[5], row_number)


def parse_vertical_blocks(lines):
    rows = []

    current_question = None
    current_options = {}
    current_correct = None
    current_row_number = None

    def flush_current():
        nonlocal current_question, current_options, current_correct, current_row_number

        if current_question or current_options or current_correct:
            rows.append(
                make_import_row(
                    current_question or "",
                    current_options.get("a", ""),
                    current_options.get("b", ""),
                    current_options.get("c", ""),
                    current_options.get("d", ""),
                    current_correct or "",
                    current_row_number,
                )
            )

        current_question = None
        current_options = {}
        current_correct = None
        current_row_number = None

    for row_number, raw_line in lines:
        line = normalize_import_value(raw_line)
        if not line:
            continue

        option_data = parse_option_line(line)
        if option_data:
            key, value = option_data
            current_options[key] = value
            continue

        correct_data = parse_correct_line(line)
        if correct_data:
            current_correct = correct_data
            flush_current()
            continue

        # Gặp câu mới khi câu cũ đã có dữ liệu thì đóng câu cũ.
        if current_question and current_options:
            flush_current()

        current_question = line
        current_row_number = row_number

    flush_current()
    return rows


def parse_text_import(text: str):
    text = text.replace("\ufeff", "")
    lines = [(idx, line) for idx, line in enumerate(text.splitlines(), start=1) if normalize_import_value(line)]

    horizontal_rows = []
    vertical_source = []

    for row_number, line in lines:
        row = parse_horizontal_line(line, row_number)
        if row:
            horizontal_rows.append(row)
        else:
            vertical_source.append((row_number, line))

    vertical_rows = parse_vertical_blocks(vertical_source)

    rows = []
    rows.extend(horizontal_rows)
    rows.extend(vertical_rows)

    return rows


def rows_from_dataframe(df: pd.DataFrame):
    df = auto_map_dataframe(df)
    rows = []
    for idx, item in enumerate(df.fillna("").to_dict(orient="records"), start=1):
        rows.append(
            make_import_row(
                item.get("question_text", ""),
                item.get("option_a", ""),
                item.get("option_b", ""),
                item.get("option_c", ""),
                item.get("option_d", ""),
                item.get("correct", ""),
                idx,
            )
        )
    return rows


def parse_import_file(content: bytes, filename: str):
    name = (filename or "").lower()

    if name.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(content))
        return rows_from_dataframe(df)

    if name.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="ignore")
        # Ưu tiên parser text vì đọc được cả không header.
        rows = parse_text_import(text)
        if rows:
            return rows

        delimiter = detect_delimiter(text[:500])
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", sep=delimiter, on_bad_lines="skip", engine="python")
        return rows_from_dataframe(df)

    if name.endswith(".txt") or name.endswith(".md"):
        text = content.decode("utf-8-sig", errors="ignore")
        return parse_text_import(text)

    raise HTTPException(400, "Định dạng file không hỗ trợ. Hãy dùng .txt, .md, .csv hoặc .xlsx.")

# ======================================================
# 12) IMPORT — UPLOAD PAGE
# ======================================================
@router.get("/{quiz_id}/import", response_class=HTMLResponse)
def import_upload(
    quiz_id: str, request: Request,
    db=Depends(get_db), teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/import_upload.html",
        {"request": request, "quiz": quiz}
    )


# ======================================================
# 13) IMPORT — PREVIEW
# ======================================================
@router.post("/{quiz_id}/import/preview", response_class=HTMLResponse)
async def import_preview(
    quiz_id: str,
    request: Request,
    file: UploadFile = File(...),
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    content = await file.read()
    rows = parse_import_file(content, file.filename or "")

    valid_rows = [r for r in rows if r.get("is_valid")]
    invalid_rows = [r for r in rows if not r.get("is_valid")]

    cache = ensure_import_cache(request)
    uid = request.session.get("user_id") or teacher.id
    key = f"import_quiz_{quiz_id}_{uid}"
    cache[key] = rows

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/import_preview.html",
        {
            "request": request,
            "quiz": quiz,
            "quiz_id": quiz_id,
            "questions": rows,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows,
            "valid_count": len(valid_rows),
            "invalid_count": len(invalid_rows),
            "total_rows": len(rows),
            "filename": file.filename,
        }
    )


# ======================================================
# 14) IMPORT — CONFIRM SAVE
# ======================================================
@router.post("/{quiz_id}/import/confirm", response_class=HTMLResponse)
def import_confirm(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    cache = ensure_import_cache(request)
    uid = request.session.get("user_id") or teacher.id
    key = f"import_quiz_{quiz_id}_{uid}"
    questions = cache.get(key)

    if not questions:
        raise HTTPException(
            400,
            "Không có dữ liệu để import. Vui lòng quay lại bước chọn file."
        )

    valid_questions = [q for q in questions if q.get("is_valid")]
    invalid_questions = [q for q in questions if not q.get("is_valid")]

    if not valid_questions:
        raise HTTPException(400, "Không có câu hỏi hợp lệ để import.")

    added_count = 0
    existed_count = db.query(Question).filter(Question.quiz_id == quiz_id).count()

    for idx, q in enumerate(valid_questions, start=1):
        text = normalize_import_value(q.get("question_text"))
        a = normalize_import_value(q.get("option_a"))
        b = normalize_import_value(q.get("option_b"))
        c = normalize_import_value(q.get("option_c"))
        d = normalize_import_value(q.get("option_d"))
        correct = normalize_correct_answer(q.get("correct"))

        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=quiz_id,
            question_type="multiple_choice",
            question_text=text,
            points=1,
            difficulty_level="medium",
            question_order=existed_count + idx,
        )
        db.add(new_q)
        db.flush()

        options = {
            "a": a,
            "b": b,
            "c": c,
            "d": d,
        }

        for order, (key_opt, val) in enumerate(options.items(), start=1):
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=val,
                is_correct=1 if correct == key_opt else 0,
                option_order=order,
            ))

        added_count += 1

    db.flush()
    refresh_total_questions(db, quiz)
    db.commit()
    cache.pop(key, None)

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/import_confirm.html",
        {
            "request": request,
            "quiz": quiz,
            "added_count": added_count,
            "skipped_count": len(invalid_questions),
            "total_rows": len(questions),
        }
    )


# ======================================================
# 15) CREATE QUESTION – PAGE
# ======================================================
@router.get("/{quiz_id}/question/create", response_class=HTMLResponse)
def create_question_page(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/question_create.html",
        {
            "request": request,
            "quiz": quiz
        }
    )


# ======================================================
# 16) CREATE QUESTION – POST
# ======================================================
@router.post("/{quiz_id}/question/create")
def create_question_post(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),

    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...),
    points: float = Form(1),
    explanation: str = Form(""),
    difficulty_level: str = Form("medium"),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    existed_count = db.query(Question).filter(Question.quiz_id == quiz_id).count()

    new_q = Question(
        id=str(uuid.uuid4()),
        quiz_id=quiz_id,
        question_type="multiple_choice",
        question_text=question_text.strip(),
        explanation=explanation.strip() if explanation else None,
        points=points or 1,
        difficulty_level=difficulty_level if difficulty_level in ["easy", "medium", "hard"] else "medium",
        question_order=existed_count + 1,
    )
    db.add(new_q)
    db.flush()

    options = {
        "a": option_a,
        "b": option_b,
        "c": option_c,
        "d": option_d,
    }

    correct = normalize_correct_answer(correct)

    for order, (key, text) in enumerate(options.items(), start=1):
        text = text.strip()
        if text:
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=text,
                is_correct=1 if correct == key else 0,
                option_order=order,
            ))

    db.flush()
    refresh_total_questions(db, quiz)
    db.commit()

    return RedirectResponse(
        f"/teacher/quizzes/detail/{quiz_id}", 303
    )



# ======================================================
# 17) EDIT QUESTION – PAGE
# ======================================================
@router.get("/{quiz_id}/question/edit/{question_id}", response_class=HTMLResponse)
def edit_question_page(
    quiz_id: str,
    question_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    question = (
        db.query(Question)
        .options(joinedload(Question.options))
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/question_edit.html",
        {
            "request": request,
            "quiz": quiz,
            "question": question,
        },
    )


# ======================================================
# 18) EDIT QUESTION – POST
# ======================================================
@router.post("/{quiz_id}/question/edit/{question_id}")
def edit_question_post(
    quiz_id: str,
    question_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),

    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...),
    points: float = Form(1),
    explanation: str = Form(""),
    difficulty_level: str = Form("medium"),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    question = (
        db.query(Question)
        .options(joinedload(Question.options))
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    question.question_text = question_text.strip()
    question.explanation = explanation.strip() if explanation else None
    question.points = points or 1
    question.difficulty_level = difficulty_level if difficulty_level in ["easy", "medium", "hard"] else "medium"

    old_options = sorted(list(question.options or []), key=lambda x: x.option_order or 0)

    option_values = [
        ("a", option_a.strip()),
        ("b", option_b.strip()),
        ("c", option_c.strip()),
        ("d", option_d.strip()),
    ]
    correct = normalize_correct_answer(correct)

    for index, (key, text) in enumerate(option_values, start=1):
        if index <= len(old_options):
            opt = old_options[index - 1]
            opt.option_text = text
            opt.is_correct = 1 if correct == key else 0
            opt.option_order = index
        else:
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=question.id,
                option_text=text,
                is_correct=1 if correct == key else 0,
                option_order=index,
            ))

    # Nếu cũ có hơn 4 đáp án thì xóa phần dư để giao diện A/B/C/D nhất quán.
    if len(old_options) > 4:
        for opt in old_options[4:]:
            db.delete(opt)

    db.commit()

    return RedirectResponse(
        f"/teacher/quizzes/detail/{quiz_id}", 303
    )


# ======================================================
# 19) DELETE QUESTION – PAGE
# ======================================================
@router.get("/{quiz_id}/question/delete/{question_id}", response_class=HTMLResponse)
def delete_question_page(
    quiz_id: str,
    question_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    question = (
        db.query(Question)
        .options(joinedload(Question.options))
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    attempts_count = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).count()

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/question_delete.html",
        {
            "request": request,
            "quiz": quiz,
            "question": question,
            "attempts_count": attempts_count,
        },
    )


# ======================================================
# 20) DELETE QUESTION – POST
# ======================================================
@router.post("/{quiz_id}/question/delete/{question_id}")
def delete_question_post(
    quiz_id: str,
    question_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    db.delete(question)
    db.flush()
    refresh_total_questions(db, quiz)
    db.commit()

    return RedirectResponse(
        f"/teacher/quizzes/detail/{quiz_id}", 303
    )


# ======================================================
# 21) EXPORT QUIZ RESULTS – EXCEL
# ======================================================
@router.get("/export/{quiz_id}")
def export_quiz_results(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher),
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.user).joinedload(User.profile))
        .filter(QuizAttempt.quiz_id == quiz_id)
        .order_by(
            case((QuizAttempt.submitted_at.is_(None), 1), else_=0),
            QuizAttempt.submitted_at.desc(),
            QuizAttempt.started_at.desc(),
        )
        .all()
    )

    rows = []
    for a in attempts:
        student_name = "Không rõ"
        if a.user:
            if getattr(a.user, "profile", None) and a.user.profile.full_name:
                student_name = a.user.profile.full_name
            else:
                student_name = a.user.username or a.user.email or "Không rõ"

        rows.append({
            "Học viên": student_name,
            "Email": a.user.email if a.user else "",
            "Lần làm": a.attempt_number,
            "Điểm": float(a.score or 0),
            "Số câu đúng": a.correct_answers or 0,
            "Tổng số câu": a.total_questions or 0,
            "Thời gian làm (giây)": a.time_spent_seconds or 0,
            "Trạng thái": a.status,
            "Bắt đầu": a.started_at.strftime("%d/%m/%Y %H:%M") if a.started_at else "",
            "Nộp bài": a.submitted_at.strftime("%d/%m/%Y %H:%M") if a.submitted_at else "",
        })

    output = io.BytesIO()
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame([{"Thông báo": "Chưa có bài làm nào"}])

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ket qua quiz")

    output.seek(0)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", quiz.title or "quiz")
    filename = f"quiz_results_{safe_name}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ======================================================
# 22) TEMPLATE LIST
# ======================================================
@router.get("/templates", response_class=HTMLResponse)
def quiz_templates(request: Request, db=Depends(get_db), teacher=Depends(get_current_teacher)):
    tpl = get_template_by_path(request.url.path)
    templates = db.query(QuizTemplate).filter(
        (QuizTemplate.is_public == 1) |
        (QuizTemplate.created_by == teacher.id)
    ).all()

    return tpl.TemplateResponse(
        "quizzes/template_list.html",
        {"request": request, "templates": templates}
    )