from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import traceback
import pandas as pd
from pandas.errors import ParserError
import io
import re

from app.database.connection import get_db
from app.models.quiz import Quiz
from app.models.course import Course
from app.models.question import Question
from app.models.question_option import QuestionOption

from app.config.template_config import get_template_by_path


exam_router = APIRouter(
    prefix="/admin/exams",
    tags=["Admin - Exam Management"],
)

# ================================================
# 🔹 Helper parse text → block question
# ================================================

def normalize_question_block(text_block: str) -> dict:
    lines = [l.strip() for l in text_block.splitlines() if l.strip()]
    if not lines:
        return {}

    q = {
        "question_text": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct": "",
    }

    q["question_text"] = re.sub(r"[,\s]+$", "", lines[0])

    for line in lines[1:]:
        if re.match(r"^A[\.\):]\s*", line, re.IGNORECASE):
            q["option_a"] = re.sub(r"^A[\.\):]\s*", "", line, flags=re.IGNORECASE)
        elif re.match(r"^B[\.\):]\s*", line, re.IGNORECASE):
            q["option_b"] = re.sub(r"^B[\.\):]\s*", "", line, flags=re.IGNORECASE)
        elif re.match(r"^C[\.\):]\s*", line, re.IGNORECASE):
            q["option_c"] = re.sub(r"^C[\.\):]\s*", "", line, flags=re.IGNORECASE)
        elif re.match(r"^D[\.\):]\s*", line, re.IGNORECASE):
            q["option_d"] = re.sub(r"^D[\.\):]\s*", "", line, flags=re.IGNORECASE)

        lower_line = line.lower()
        if "đáp án đúng" in lower_line or "dap an dung" in lower_line or "answer" in lower_line:
            correct = re.sub(r".*:\s*", "", line)
            correct = correct.strip().upper()
            if correct:
                q["correct"] = correct[0]

    return q


def parse_free_text_questions(raw_text: str):
    blocks = re.split(r"\n\s*\n", raw_text.strip(), flags=re.MULTILINE)
    questions = []
    for block in blocks:
        q = normalize_question_block(block)
        if q.get("question_text") and (q.get("option_a") or q.get("option_b")):
            questions.append(q)
    return questions


# ================================================
# 🔹 Normalize Excel / CSV
# ================================================

def normalize_questions_from_df(df: pd.DataFrame):
    df = df.fillna("")
    raw_columns = list(df.columns)
    columns = [str(c).strip().lower() for c in raw_columns]

    col_map = {
        "question_text": None,
        "option_a": None,
        "option_b": None,
        "option_c": None,
        "option_d": None,
        "correct": None,
    }

    for idx, col in enumerate(columns):
        if col in ["question_text", "question", "câu hỏi", "cau hoi"]:
            col_map["question_text"] = raw_columns[idx]
        elif col in ["option_a", "a"]:
            col_map["option_a"] = raw_columns[idx]
        elif col in ["option_b", "b"]:
            col_map["option_b"] = raw_columns[idx]
        elif col in ["option_c", "c"]:
            col_map["option_c"] = raw_columns[idx]
        elif col in ["option_d", "d"]:
            col_map["option_d"] = raw_columns[idx]
        elif col in ["correct", "answer", "đáp án", "dap an"]:
            col_map["correct"] = raw_columns[idx]

    if not col_map["question_text"]:
        return []

    questions = []
    for _, row in df.iterrows():
        q = {
            "question_text": str(row[col_map["question_text"]]).strip()
            if col_map["question_text"] else "",
            "option_a": str(row[col_map["option_a"]]).strip()
            if col_map["option_a"] else "",
            "option_b": str(row[col_map["option_b"]]).strip()
            if col_map["option_b"] else "",
            "option_c": str(row[col_map["option_c"]]).strip()
            if col_map["option_c"] else "",
            "option_d": str(row[col_map["option_d"]]).strip()
            if col_map["option_d"] else "",
            "correct": str(row[col_map["correct"]]).strip().upper()
            if col_map["correct"] else "",
        }
        if any(q.values()):
            questions.append(q)

    return questions


# ================================================
# 📝 Manage list
# ================================================

@exam_router.get("/manage", response_class=HTMLResponse)
def manage_exams(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    exams = (
        db.query(Quiz)
        .filter(Quiz.quiz_type == "graded")
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return tpl.TemplateResponse("exams/manage.html", {"request": request, "exams": exams})


# ================================================
# 📥 IMPORT — FORM UPLOAD
# ================================================

@exam_router.get("/{exam_id}/import", response_class=HTMLResponse)
def import_questions_form(request: Request, exam_id: str):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/import.html", {"request": request, "exam_id": exam_id})


# ================================================
# 📥 IMPORT — UPLOAD FILE (CHẠY OK 50MB)
# ================================================

@exam_router.post("/{exam_id}/import")
async def import_questions_upload(request: Request, exam_id: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = (file.filename or "").lower()

        questions = []

        if filename.endswith(".txt"):
            raw = content.decode("utf-8", errors="ignore")
            questions = parse_free_text_questions(raw)
        else:
            try:
                if filename.endswith(".xlsx"):
                    df = pd.read_excel(io.BytesIO(content))
                else:
                    df = pd.read_csv(io.BytesIO(content), encoding="utf-8", engine="python")

                questions = normalize_questions_from_df(df)

                if not questions:
                    raw = content.decode("utf-8", errors="ignore")
                    questions = parse_free_text_questions(raw)

            except ParserError:
                raw = content.decode("utf-8", errors="ignore")
                questions = parse_free_text_questions(raw)

        if not questions:
            raise HTTPException(400, "Không đọc được dữ liệu câu hỏi từ file.")

        # 🔥 Lưu cache server-side (cho file 50MB)
        token = str(uuid.uuid4())
        request.app.state.import_cache[token] = {
            "questions": questions,
            "exam_id": exam_id,
            "created": datetime.utcnow()
        }

        # Chỉ lưu token nhỏ vào session
        request.session["import_token"] = token

        return RedirectResponse(f"/admin/exams/{exam_id}/import/review", 303)

    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", 500)


# ================================================
# 👀 REVIEW IMPORT — (Đọc từ server-side RAM)
# ================================================

@exam_router.get("/{exam_id}/import/review", response_class=HTMLResponse)
def review_import_questions(request: Request, exam_id: str):
    tpl = get_template_by_path(request.url.path)

    token = request.session.get("import_token")
    if not token:
        raise HTTPException(400, "Không có dữ liệu import")

    cache = request.app.state.import_cache.get(token)
    if not cache:
        raise HTTPException(400, "Không có dữ liệu import")

    questions = cache["questions"]

    return tpl.TemplateResponse(
        "exams/import_review.html",
        {"request": request, "questions": questions, "exam_id": exam_id},
    )


# ================================================
# ✅ CONFIRM IMPORT — LƯU VÀO DB
# ================================================

@exam_router.post("/{exam_id}/import/confirm")
def confirm_import_questions(exam_id: str, request: Request, db: Session = Depends(get_db)):

    token = request.session.get("import_token")
    if not token:
        raise HTTPException(400, "Không có dữ liệu import")

    cache = request.app.state.import_cache.get(token)
    if not cache:
        raise HTTPException(400, "Không có dữ liệu import")

    questions = cache["questions"]

    try:
        for q in questions:
            if not q.get("question_text"):
                continue

            qid = str(uuid.uuid4())

            question = Question(
                id=qid,
                quiz_id=exam_id,
                question_text=q.get("question_text", ""),
                explanation=q.get("explanation"),
                question_order=0,
            )
            db.add(question)

            options = [
                ("A", "option_a"),
                ("B", "option_b"),
                ("C", "option_c"),
                ("D", "option_d"),
            ]

            for idx, (label, key) in enumerate(options, start=1):
                text = q.get(key, "")
                if not text:
                    continue

                db.add(
                    QuestionOption(
                        id=str(uuid.uuid4()),
                        question_id=qid,
                        option_text=text,
                        is_correct=1 if label == q.get("correct", "").upper() else 0,
                        option_order=idx,
                    )
                )

        db.commit()

        # 🔥 Xoá RAM + session sau khi nhập xong
        request.app.state.import_cache.pop(token, None)
        request.session.pop("import_token", None)

        return RedirectResponse("/admin/exams/manage", 303)

    except Exception:
        db.rollback()
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", 500)
