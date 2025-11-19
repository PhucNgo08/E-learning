"""
=============================================================
🎓 ROUTER: Teacher – Quiz Management (v16.5 ULTRA FINAL)
Hoàn chỉnh 100%:
- CRUD Practice + Graded Quiz
- Import TXT / CSV / XLSX using SERVER-SIDE CACHE
- Auto-mapping headers + auto-fill missing columns
- Không dùng cookie để lưu dữ liệu → KHÔNG BAO GIỜ mất session
- Statistics + Score Chart API
=============================================================
"""
from app.models.quiz_template import QuizTemplate

from fastapi import (
    APIRouter, Request, Depends, Form,
    UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import pandas as pd
import uuid, io

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
):

    time_limit_minutes = int(time_limit_minutes)
    max_attempts = int(max_attempts)
    total_questions = int(total_questions)
    passing_score = float(passing_score)

    if quiz_type == "graded":
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
            available_from=datetime.utcnow(),
            available_to=datetime.utcnow().replace(hour=23, minute=59),
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
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    time_limit_minutes = int(time_limit_minutes)
    max_attempts = int(max_attempts)
    total_questions = int(total_questions)
    passing_score = float(passing_score)

    if mode == "graded":
        update_exam(
            db=db, user_id=teacher.id, role="teacher",
            exam_id=quiz_id,
            title=title,
            description=description,
            total_questions=total_questions,
            time_limit=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            available_from=quiz.available_from,
            available_to=quiz.available_to
        )
    else:
        update_quiz(
            db=db, teacher_id=teacher.id, quiz_id=quiz_id,
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
        .filter(QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.status == "submitted")
        .all()
    )

    buckets = [0, 0, 0, 0]
    for a in attempts:
        s = a[0] or 0
        if s < 50: buckets[0] += 1
        elif s < 70: buckets[1] += 1
        elif s < 90: buckets[2] += 1
        else: buckets[3] += 1

    return JSONResponse({"counts": buckets})


# ======================================================
# 11) IMPORT — UPLOAD PAGE
# ======================================================
REQUIRED_COLS = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct"]

HEADER_ALIASES = {
    "question": "question_text",
    "question_text": "question_text",
    "questiontext": "question_text",
    "q": "question_text",
    "noi_dung": "question_text",
    "nội_dung": "question_text",
    "câu_hỏi": "question_text",
    "cau_hoi": "question_text",

    "a": "option_a", "pa": "option_a", "option1": "option_a",
    "b": "option_b", "pb": "option_b", "option2": "option_b",
    "c": "option_c", "pc": "option_c", "option3": "option_c",
    "d": "option_d", "pd": "option_d", "option4": "option_d",

    "correct": "correct", 
    "answer": "correct",
    "correct_answer": "correct",
    "dap_an": "correct",
    "đáp_án": "correct",
}


def detect_delimiter(text: str):
    if "|" in text: return "|"
    if ";" in text: return ";"
    if "\t" in text: return "\t"
    return ","


def auto_map_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa: auto-map, tự thêm cột, tự sửa header
    """

    raw_cols = list(df.columns)

    # CASE 1 — file không có header (0,1,2...)
    if all(str(c).isdigit() for c in raw_cols):

        # thêm cột cho đủ
        while len(raw_cols) < 6:
            df[len(df.columns)] = ""

        df = df.iloc[:, :6]
        df.columns = REQUIRED_COLS
        return df

    # CASE 2 — có header nhưng sai định dạng
    normalized = [
        str(c).lower().strip().replace(" ", "_").replace("-", "_")
        for c in raw_cols
    ]

    mapped = [HEADER_ALIASES.get(c) for c in normalized]

    # nếu map toàn bộ đều None → fallback chuẩn
    if all(m is None for m in mapped):
        while len(raw_cols) < 6:
            df[len(df.columns)] = ""

        df = df.iloc[:, :6]
        df.columns = REQUIRED_COLS
        return df

    final_cols = []
    for i, col in enumerate(mapped):
        final_cols.append(col or f"col_{i}")

    df.columns = final_cols

    # thêm cột thiếu
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""

    return df[REQUIRED_COLS]


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
#     🔥 SỬ DỤNG SERVER-SIDE CACHE (KHÔNG LƯU VÀO COOKIE)
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
    name = file.filename.lower()

    # đọc file
    try:
        if name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content), header=None)
        elif name.endswith(".csv"):
            sample = content.decode("utf-8", errors="ignore")[:200]
            delimiter = detect_delimiter(sample)
            df = pd.read_csv(
                io.BytesIO(content),
                encoding="utf-8",
                sep=delimiter,
                on_bad_lines="skip",
                header=None,
                engine="python"
            )
        elif name.endswith(".txt"):
            lines = content.decode("utf-8", errors="ignore").splitlines()
            df = pd.DataFrame([row.split("|") for row in lines])
        else:
            raise HTTPException(400, "Định dạng file không hỗ trợ.")
    except Exception as e:
        raise HTTPException(400, f"Lỗi đọc file: {e}")

    # chuẩn hóa
    df = auto_map_dataframe(df)
    questions = df.to_dict(orient="records")

    # ======================================================
    # LƯU SERVER-SIDE CACHE (không bao giờ mất như cookie)
    # ======================================================
    uid = request.session.get("user_id")

    key = f"import_quiz_{quiz_id}_{uid}"

    request.app.state.import_cache[key] = questions

    print("🔥 PREVIEW SAVED:", key, "TOTAL:", len(questions))

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "quizzes/import_preview.html",
        {
            "request": request,
            "quiz": quiz,
            "quiz_id": quiz_id,
            "questions": questions
        }
    )


# ======================================================
# 14) IMPORT — CONFIRM SAVE (FIXED v16.6)
# ======================================================
@router.post("/{quiz_id}/import/confirm")
def import_confirm(
    quiz_id: str,
    request: Request,
    db=Depends(get_db),
    teacher=Depends(get_current_teacher)
):

    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    uid = request.session.get("user_id")
    key = f"import_quiz_{quiz_id}_{uid}"

    questions = request.app.state.import_cache.get(key)
    print("🔥 CONFIRM LOAD:", key, "| DATA:", len(questions) if questions else "None")

    if not questions:
        raise HTTPException(
            400,
            "Không có dữ liệu để import. Vui lòng làm lại bước Upload."
        )

    # ------------------------------------------------------
    # Hàm chuẩn hóa giá trị thành string an toàn
    # ------------------------------------------------------
    def normalize(v):
        """
        Chuẩn hóa mọi giá trị:
        - None → ""
        - float/NaN → ""
        - int/float → "..."
        - string → strip()
        """
        if v is None:
            return ""

        # Nếu là float nhưng là NaN → bỏ
        if isinstance(v, float):
            if pd.isna(v):
                return ""
            return str(v).strip()

        # Convert mọi thứ còn lại thành chuỗi
        return str(v).strip()

    # ======================================================
    # LƯU DB AN TOÀN
    # ======================================================
    for q in questions:

        # ----- Question text -----
        text = normalize(q.get("question_text"))
        if not text:
            continue

        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=quiz_id,
            question_text=text
        )
        db.add(new_q)
        db.flush()

        # ----- Options A → D -----
        for opt in ["option_a", "option_b", "option_c", "option_d"]:
            val = normalize(q.get(opt))
            if not val:
                continue

            correct_raw = normalize(q.get("correct")).lower()

            # EXCEL/TXT/CSV có thể ghi:
            # A / a / Option_A / 1 / "Đáp án A" → phải nhận đúng
            is_correct = (
                correct_raw == opt[-1] or
                correct_raw == opt or
                correct_raw == val.lower()
            )

            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=val,
                is_correct=is_correct
            ))

    db.commit()

    # Xoá cache sau khi lưu
    request.app.state.import_cache.pop(key, None)

    return RedirectResponse(f"/teacher/quizzes/detail/{quiz_id}", 303)
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
    correct: str = Form(...),       # "a" | "b" | "c" | "d"
):
    quiz, mode = auto_get_quiz(db, teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz không tồn tại.")

    # Tạo question
    new_q = Question(
        id=str(uuid.uuid4()),
        quiz_id=quiz_id,
        question_text=question_text.strip()
    )
    db.add(new_q)
    db.flush()

    # Thêm option
    options = {
        "a": option_a,
        "b": option_b,
        "c": option_c,
        "d": option_d,
    }

    for key, text in options.items():
        if text.strip():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=text.strip(),
                is_correct=(correct == key)
            ))

    db.commit()

    return RedirectResponse(
        f"/teacher/quizzes/detail/{quiz_id}", 303
    )
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
