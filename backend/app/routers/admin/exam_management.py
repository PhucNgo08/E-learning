"""
==========================================================
🛡️ ADMIN — EXAM MANAGEMENT ROUTER (FULL v5.2 FIX)
Quản lý kỳ thi (Quiz graded)
+ Danh sách kỳ thi
+ Tạo / Sửa / Xóa kỳ thi
+ Duyệt / Từ chối
+ Import câu hỏi (XLSX / CSV / TXT)
  ✔ CSV dạng text-block (không cần bảng) — đã FIX
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import pandas as pd
import io
import re

from app.database.connection import get_db
from app.models.quiz import Quiz
from app.models.course import Course
from app.models.question import Question
from app.models.question_option import QuestionOption

from app.services.admin.exam_management_service import (
    get_exams,
    create_exam,
    update_exam,
    delete_exam,
    approve_exam,
    reject_exam
)

from app.config.template_config import get_template_by_path


# ==========================================================
# 🔧 TXT / CSV dạng text-block Parser
# ==========================================================
def normalize_question_block(text_block: str) -> dict:
    """Chuyển block TXT thành object câu hỏi."""

    lines = [l.strip() for l in text_block.splitlines() if l.strip()]
    if not lines:
        return {
            "question_text": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct": ""
        }

    q = {
        "question_text": lines[0],
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct": "",
    }

    for line in lines[1:]:
        if re.match(r"^A[\.\):]\s*", line, re.I):
            q["option_a"] = re.sub(r"^A[\.\):]\s*", "", line)

        elif re.match(r"^B[\.\):]\s*", line, re.I):
            q["option_b"] = re.sub(r"^B[\.\):]\s*", "", line)

        elif re.match(r"^C[\.\):]\s*", line, re.I):
            q["option_c"] = re.sub(r"^C[\.\):]\s*", "", line)

        elif re.match(r"^D[\.\):]\s*", line, re.I):
            q["option_d"] = re.sub(r"^D[\.\):]\s*", "", line)

        # Đáp án
        if "đáp án" in line.lower() or "answer" in line.lower():
            q["correct"] = line.split(":")[-1].strip().upper()[0:1]

    return q


# ==========================================================
# 📌 ROUTER CONFIG
# ==========================================================
exam_router = APIRouter(
    prefix="/admin/exams",
    tags=["Admin - Exams"],
)


# ==========================================================
# 📋 1) Danh sách kỳ thi
# ==========================================================
@exam_router.get("/manage", response_class=HTMLResponse)
def exam_manage(request: Request, db: Session = Depends(get_db)):

    tpl = get_template_by_path(request.url.path)
    exams = get_exams(db, user_id="admin", role="admin")

    return tpl.TemplateResponse(
        "exams/manage.html",
        {"request": request, "exams": exams}
    )


# ==========================================================
# ➕ 2) Tạo kỳ thi — GET
# ==========================================================
@exam_router.get("/create", response_class=HTMLResponse)
def exam_create_form(request: Request, db: Session = Depends(get_db)):

    tpl = get_template_by_path(request.url.path)
    courses = db.query(Course).all()

    return tpl.TemplateResponse(
        "exams/create.html",
        {"request": request, "courses": courses}
    )


# ==========================================================
# ➕ 3) Tạo kỳ thi — POST
# ==========================================================
@exam_router.post("/create")
def exam_create(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    course_id: str = Form(...),
    total_questions: int = Form(...),
    time_limit: int = Form(...),
    max_attempts: int = Form(...),
    passing_score: float = Form(...),
    available_from: str = Form(None),
    available_to: str = Form(None)
):

    af = datetime.fromisoformat(available_from) if available_from else None
    at = datetime.fromisoformat(available_to) if available_to else None

    create_exam(
        db=db,
        user_id="admin",
        role="admin",
        title=title,
        description=description,
        course_id=course_id,
        total_questions=total_questions,
        time_limit=time_limit,
        max_attempts=max_attempts,
        passing_score=passing_score,
        available_from=af,
        available_to=at,
    )

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ✏️ 4) Edit — GET
# ==========================================================
@exam_router.get("/{exam_id}/edit", response_class=HTMLResponse)
def exam_edit_form(exam_id: str, request: Request, db: Session = Depends(get_db)):

    tpl = get_template_by_path(request.url.path)

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    courses = db.query(Course).all()

    return tpl.TemplateResponse(
        "exams/edit.html",
        {"request": request, "exam": exam, "courses": courses}
    )


# ==========================================================
# ✏️ 5) Edit — POST
# ==========================================================
@exam_router.post("/{exam_id}/edit")
def exam_edit(
    exam_id: str,
    request: Request,
    db: Session = Depends(get_db),

    title: str = Form(...),
    description: str = Form(""),
    total_questions: int = Form(...),
    time_limit: int = Form(...),
    max_attempts: int = Form(...),
    passing_score: float = Form(...),
    available_from: str = Form(None),
    available_to: str = Form(None),
):

    af = datetime.fromisoformat(available_from) if available_from else None
    at = datetime.fromisoformat(available_to) if available_to else None

    update_exam(
        db=db,
        user_id="admin",
        role="admin",
        exam_id=exam_id,
        title=title,
        description=description,
        total_questions=total_questions,
        time_limit=time_limit,
        max_attempts=max_attempts,
        passing_score=passing_score,
        available_from=af,
        available_to=at,
    )

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ❌ 6) Delete
# ==========================================================
@exam_router.get("/{exam_id}/delete")
def exam_delete(exam_id: str, db: Session = Depends(get_db)):

    delete_exam(db, user_id="admin", role="admin", exam_id=exam_id)
    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ✔️ 7) Approve
# ==========================================================
@exam_router.get("/{exam_id}/approve")
def admin_approve(exam_id: str, db: Session = Depends(get_db)):
    approve_exam(db, exam_id)
    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ❌ 8) Reject
# ==========================================================
@exam_router.get("/{exam_id}/reject")
def admin_reject(exam_id: str, db: Session = Depends(get_db)):
    reject_exam(db, exam_id)
    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# 📥 9) Import — GET
# ==========================================================
@exam_router.get("/{exam_id}/import", response_class=HTMLResponse)
def exam_import_form(exam_id: str, request: Request, db: Session = Depends(get_db)):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    tpl = get_template_by_path(request.url.path)

    return tpl.TemplateResponse(
        "exams/import.html",
        {"request": request, "exam": exam, "exam_id": exam_id}
    )


# ==========================================================
# 📥 10) Import — POST (FIXED CSV)
# ==========================================================
@exam_router.post("/{exam_id}/import")
async def exam_import_submit(
    exam_id: str,
    db: Session = Depends(get_db),
    file: UploadFile = File(...)
):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    # --- đọc file
    try:
        content = await file.read()
        filename = file.filename.lower()

        # Excel
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))

        # CSV (NHƯNG KHÔNG CÓ CẤU TRÚC BẢNG) → XỬ LÝ NHƯ TXT
        elif filename.endswith(".csv"):
            text = content.decode("utf-8-sig", errors="ignore")
            blocks = [b for b in text.split("\n\n") if b.strip()]
            df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        # TXT
        elif filename.endswith(".txt"):
            text = content.decode("utf-8-sig", errors="ignore")
            blocks = [b for b in text.split("\n\n") if b.strip()]
            df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        else:
            raise HTTPException(400, "Chỉ hỗ trợ XLSX / CSV / TXT.")

    except Exception as e:
        raise HTTPException(400, f"Lỗi đọc file ({e})")

    # =======================================================
    # 🔥 CHUẨN HOÁ TÊN CỘT
    # =======================================================
    rename_map = {
        "question": "question_text",
        "question_text": "question_text",

        "a": "option_a",
        "b": "option_b",
        "c": "option_c",
        "d": "option_d",

        "option_a": "option_a",
        "option_b": "option_b",
        "option_c": "option_c",
        "option_d": "option_d",

        "correct": "correct",
        "answer": "correct",
        "correct_answer": "correct",
        "đáp án": "correct",
    }

    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns={c: rename_map.get(c, c) for c in df.columns}, inplace=True)

    # =======================================================
    # 🔥 CHECK CỘT BẮT BUỘC
    # =======================================================
    required = {"question_text", "option_a", "option_b", "option_c", "option_d", "correct"}

    if not required.issubset(df.columns):
        raise HTTPException(400, f"Thiếu cột bắt buộc: {required - set(df.columns)}")

    # =======================================================
    # 🔥 LƯU DB
    # =======================================================
    for _, row in df.iterrows():

        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=exam_id,
            question_text=str(row["question_text"]),
            difficulty_level=exam.difficulty_level,
        )
        db.add(new_q)
        db.flush()

        options = {
            "A": row["option_a"],
            "B": row["option_b"],
            "C": row["option_c"],
            "D": row["option_d"]
        }

        correct_letter = str(row["correct"]).strip().upper()[0]

        for letter, text in options.items():
            db.add(
                QuestionOption(
                    id=str(uuid.uuid4()),
                    question_id=new_q.id,
                    option_text=str(text),
                    is_correct=(letter == correct_letter),
                )
            )

    db.commit()

    return RedirectResponse(f"/admin/exams/{exam_id}/edit", 303)
