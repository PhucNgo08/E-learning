"""
==========================================================
🛡️ ADMIN — EXAM MANAGEMENT ROUTER (v11.0 PRO MAX 2025)
==========================================================
- CRUD Exam (Create / Edit / Delete)
- Approve / Reject
- Import Engine V12 PRO
- Validate đầu vào + bắt lỗi đẹp
- Tối ưu redirect + hiển thị thông báo
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form,
    UploadFile, File, HTTPException
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
    reject_exam,
    update_question_count
)

from app.config.template_config import get_template_by_path


# ==========================================================
# 🔧 TXT BLOCK PARSER V10.3 – FIX chuẩn 100%
# ==========================================================
def normalize_question_block(text_block: str) -> dict:
    """
    Parse dạng:
    Câu hỏi ?
    A. ...
    B. ...
    C. ...
    D. ...
    Đáp án đúng: B
    """

    pattern = r"""
        (?P<q>.+?)\n
        A[\.\):]\s*(?P<a>.+?)\n
        B[\.\):]\s*(?P<b>.+?)\n
        C[\.\):]\s*(?P<c>.+?)\n
        D[\.\):]\s*(?P<d>.+?)\n
        .*?(Đáp\s*án\s*đúng|Answer)\s*[:：]\s*(?P<correct>[A-Da-d])
    """

    m = re.search(pattern, text_block, flags=re.I | re.S | re.X)

    if not m:
        return {
            "question_text": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct": ""
        }

    return {
        "question_text": m.group("q").strip(),
        "option_a": m.group("a").strip(),
        "option_b": m.group("b").strip(),
        "option_c": m.group("c").strip(),
        "option_d": m.group("d").strip(),
        "correct": m.group("correct").upper().strip()
    }


# ==========================================================
# 📌 ROUTER CONFIG
# ==========================================================
exam_router = APIRouter(
    prefix="/admin/exams",
    tags=["Admin - Exams"],
)


# ==========================================================
# 📋 1) MANAGE EXAMS
# ==========================================================
@exam_router.get("/manage", response_class=HTMLResponse)
def exam_manage(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    exams = get_exams(db, user_id="admin", role="admin")

    return tpl.TemplateResponse("exams/manage.html", {
        "request": request,
        "exams": exams
    })


# ==========================================================
# ➕ 2) CREATE – GET
# ==========================================================
@exam_router.get("/create", response_class=HTMLResponse)
def exam_create_form(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    courses = db.query(Course).order_by(Course.course_name).all()

    return tpl.TemplateResponse("exams/create.html", {
        "request": request,
        "courses": courses
    })


# ==========================================================
# ➕ 3) CREATE – POST (SAFE VERSION)
# ==========================================================
@exam_router.post("/create")
def exam_create(
    request: Request, db: Session = Depends(get_db),

    title: str = Form(...), description: str = Form(""),
    course_id: str = Form(...),
    total_questions: int = Form(...),
    time_limit: int = Form(...),
    max_attempts: int = Form(...),
    passing_score: float = Form(...),
    available_from: str = Form(None),
    available_to: str = Form(None)
):

    try:
        af = datetime.fromisoformat(available_from) if available_from else None
        at = datetime.fromisoformat(available_to) if available_to else None

    except:
        raise HTTPException(400, "Ngày giờ không hợp lệ.")

    try:
        create_exam(
            db, "admin", "admin", title, description,
            course_id, total_questions, time_limit,
            max_attempts, passing_score, af, at
        )

    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ✏️ 4) EDIT – GET
# ==========================================================
@exam_router.get("/{exam_id}/edit", response_class=HTMLResponse)
def exam_edit_form(exam_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    courses = db.query(Course).order_by(Course.course_name).all()

    return tpl.TemplateResponse("exams/edit.html", {
        "request": request,
        "exam": exam,
        "courses": courses
    })


# ==========================================================
# ✏️ 5) EDIT – POST (SAFE VERSION)
# ==========================================================
@exam_router.post("/{exam_id}/edit")
def exam_edit(
    exam_id: str, request: Request, db: Session = Depends(get_db),

    title: str = Form(...), description: str = Form(""),
    total_questions: int = Form(...),
    time_limit: int = Form(...),
    max_attempts: int = Form(...),
    passing_score: float = Form(...),
    available_from: str = Form(None),
    available_to: str = Form(None)
):

    try:
        af = datetime.fromisoformat(available_from) if available_from else None
        at = datetime.fromisoformat(available_to) if available_to else None
    except:
        raise HTTPException(400, "Ngày giờ không hợp lệ.")

    try:
        update_exam(
            db, "admin", "admin", exam_id, title, description,
            total_questions, time_limit,
            max_attempts, passing_score, af, at
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ❌ 6) DELETE
# ==========================================================
@exam_router.get("/{exam_id}/delete")
def exam_delete(exam_id: str, db: Session = Depends(get_db)):
    try:
        delete_exam(db, "admin", "admin", exam_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# ✔️ 7) APPROVE / REJECT
# ==========================================================
@exam_router.get("/{exam_id}/approve")
def admin_approve(exam_id: str, db: Session = Depends(get_db)):
    try:
        approve_exam(db, exam_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse("/admin/exams/manage", 303)


@exam_router.get("/{exam_id}/reject")
def admin_reject(exam_id: str, db: Session = Depends(get_db)):
    try:
        reject_exam(db, exam_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse("/admin/exams/manage", 303)


# ==========================================================
# 📥 8) IMPORT – GET
# ==========================================================
@exam_router.get("/{exam_id}/import", response_class=HTMLResponse)
def exam_import_form(exam_id: str, request: Request, db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/import.html", {
        "request": request,
        "exam": exam,
        "exam_id": exam_id
    })


# ==========================================================
# 📥 9) IMPORT – POST (V12 PRO)
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

    try:
        content = await file.read()
        filename = file.filename.lower()
        df = None

        # ===================================================
        # 1) XLSX
        # ===================================================
        if filename.endswith(".xlsx"):
            temp_df = pd.read_excel(io.BytesIO(content), header=None)

            # Vertical block (1–2 columns)
            if temp_df.shape[1] <= 2:
                blocks, buf = [], []
                for _, row in temp_df.iterrows():
                    line = str(row[0]).strip()
                    if not line:
                        if buf:
                            blocks.append("\n".join(buf))
                            buf = []
                        continue
                    buf.append(line)
                if buf:
                    blocks.append("\n".join(buf))

                df = pd.DataFrame([normalize_question_block(b) for b in blocks])

            else:
                scores = temp_df.apply(lambda r: sum(len(str(x)) for x in r), axis=1)
                header = scores.idxmax()
                df = pd.read_excel(io.BytesIO(content), header=header)

        # ===================================================
        # 2) CSV — MULTI-LINE + AUTO MODE
        # ===================================================
        elif filename.endswith(".csv"):

            text = content.decode("utf-8-sig", errors="ignore")
            delimiters = [",", ";", "|", "\t"]

            for d in delimiters:
                try:
                    test = pd.read_csv(io.StringIO(text), delimiter=d)
                    if test.shape[1] >= 1:
                        df = test
                        break
                except:
                    continue

            # CSV 2-column
            if df.shape[1] == 2:
                first = str(df.iloc[0, 0]).lower().strip()
                second = str(df.iloc[0, 1]).lower().strip()
                if first in ["title", "question"] and second in ["description", "nội dung"]:
                    df = df.iloc[1:]

                rows, buffer = [], []
                for _, row in df.iterrows():
                    line = str(row.iloc[1]).strip()
                    if not line:
                        if buffer:
                            rows.append(normalize_question_block("\n".join(buffer)))
                            buffer = []
                        continue
                    buffer.append(line)

                if buffer:
                    rows.append(normalize_question_block("\n".join(buffer)))

                df = pd.DataFrame(rows)

            # CSV 6 columns chuẩn
            elif set(df.columns) >= {
                "question_text", "option_a", "option_b",
                "option_c", "option_d", "correct"
            }:
                pass

            # fallback block mode
            else:
                blocks = [b for b in text.split("\n\n") if b.strip()]
                df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        # ===================================================
        # 3) TXT BLOCK
        # ===================================================
        elif filename.endswith(".txt"):

            text = content.decode("utf-8-sig", errors="ignore")

            pattern = r"""
                (?P<block>
                    .+?
                    (?:A|a)[\.\):]\s*.+?\n
                    (?:B|b)[\.\):]\s*.+?\n
                    (?:C|c)[\.\):]\s*.+?\n
                    (?:D|d)[\.\):]\s*.+?\n
                    .*?(Đáp\s*án|Answer).*?\n?
                )
            """

            blocks = re.findall(pattern, text, flags=re.I | re.S | re.X)
            df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        else:
            raise HTTPException(400, "Chỉ hỗ trợ .xlsx / .csv / .txt")

    except Exception as e:
        raise HTTPException(400, f"Lỗi đọc file: {e}")

    # ===================================================
    # CHUẨN HÓA TÊN CỘT
    # ===================================================
    rename_map = {
        "question": "question_text",
        "title": "question_text",
        "description": "question_text",

        "a": "option_a", "b": "option_b",
        "c": "option_c", "d": "option_d",

        "correct": "correct",
        "answer": "correct"
    }

    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns={c: rename_map.get(c, c) for c in df.columns}, inplace=True)
    df = df.fillna("")

    required = {
        "question_text", "option_a",
        "option_b", "option_c",
        "option_d", "correct"
    }

    if not required.issubset(df.columns):
        raise HTTPException(400, f"Thiếu cột: {required - set(df.columns)}")

    # ===================================================
    # SAVE TO DB
    # ===================================================
    for _, row in df.iterrows():

        q_text = row["question_text"].strip()
        if not q_text:
            continue

        options = {
            "A": row["option_a"].strip(),
            "B": row["option_b"].strip(),
            "C": row["option_c"].strip(),
            "D": row["option_d"].strip()
        }

        raw_correct = row["correct"].strip().upper()
        correct_letter = next((c for c in raw_correct if c in "ABCD"), None)
        if not correct_letter:
            continue

        # tạo question
        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=exam_id,
            question_text=q_text,
            difficulty_level=exam.difficulty_level
        )
        db.add(new_q)
        db.flush()

        for letter, text in options.items():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=text,
                is_correct=(letter == correct_letter)
            ))

    db.commit()

    # 👉 TỰ ĐỘNG CẬP NHẬT TOTAL_QUESTIONS
    update_question_count(db, exam_id)

    return RedirectResponse(f"/admin/exams/{exam_id}/edit", 303)
# ==========================================================
# 📌 10) QUESTION MANAGEMENT — LIST / ADD / EDIT / DELETE
# ==========================================================

from app.services.admin.exam_management_service import (
    get_question,
    get_questions_by_exam,
    create_question,
    update_question,
    delete_question
)

# ==========================================================
# 📋 LIST QUESTIONS TRONG EXAM
# ==========================================================
@exam_router.get("/{exam_id}/questions", response_class=HTMLResponse)
def exam_question_list(exam_id: str, request: Request, db: Session = Depends(get_db)):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    questions = get_questions_by_exam(db, exam_id)

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/questions/list.html", {
        "request": request,
        "exam": exam,
        "questions": questions
    })


# ==========================================================
# ➕ ADD QUESTION — GET
# ==========================================================
@exam_router.get("/{exam_id}/questions/add", response_class=HTMLResponse)
def question_add_form(exam_id: str, request: Request, db: Session = Depends(get_db)):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/questions/add.html", {
        "request": request,
        "exam": exam
    })


# ==========================================================
# ➕ ADD QUESTION — POST
# ==========================================================
@exam_router.post("/{exam_id}/questions/add")
def question_add(
    exam_id: str,
    db: Session = Depends(get_db),
    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...)
):

    try:
        create_question(
            db, exam_id,
            question_text,
            option_a, option_b, option_c, option_d,
            correct
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)


# ==========================================================
# ✏️ EDIT QUESTION — GET
# ==========================================================
@exam_router.get("/{exam_id}/questions/{question_id}/edit", response_class=HTMLResponse)
def question_edit_form(
    exam_id: str,
    question_id: str,
    request: Request,
    db: Session = Depends(get_db)
):

    q = get_question(db, question_id)
    if not q:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    options = db.query(QuestionOption).filter(
        QuestionOption.question_id == question_id
    ).all()

    # OPTION DICT CHUẨN
    option_dict = {
        "A": "",
        "B": "",
        "C": "",
        "D": "",
    }

    correct_letter = ""

    for opt in options:
        letter = opt.option_text[0].upper()  # "A", "B", "C", "D"
        text = opt.option_text[2:].strip() if opt.option_text[1] in [")", "."] else opt.option_text
        
        if letter in option_dict:
            option_dict[letter] = text

        if opt.is_correct:
            correct_letter = letter

    tpl = get_template_by_path(request.url.path)

    return tpl.TemplateResponse("exams/questions/edit.html", {
        "request": request,
        "exam_id": exam_id,
        "question": q,
        "option_a": option_dict["A"],
        "option_b": option_dict["B"],
        "option_c": option_dict["C"],
        "option_d": option_dict["D"],
        "correct": correct_letter
    })


# ==========================================================
# ✏️ EDIT QUESTION — POST
# ==========================================================
@exam_router.post("/{exam_id}/questions/{question_id}/edit")
def question_edit(
    exam_id: str,
    question_id: str,
    db: Session = Depends(get_db),

    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...)
):

    try:
        update_question(
            db, question_id,
            question_text,
            option_a, option_b, option_c, option_d,
            correct
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)


# ==========================================================
# ❌ DELETE QUESTION
# ==========================================================
@exam_router.get("/{exam_id}/questions/{question_id}/delete")
def question_delete(exam_id: str, question_id: str, db: Session = Depends(get_db)):

    try:
        delete_question(db, question_id)
    except Exception as e:
        raise HTTPException(400, str(e))

    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)
