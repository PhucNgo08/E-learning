from fastapi import (
    APIRouter, Request, Depends, Form,
    UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
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
    update_question_count,
    get_question,
    get_questions_by_exam,
    create_question,
    update_question,
    delete_question,
)

from app.config.template_config import get_template_by_path


# ==========================================================
# 🔧 TXT BLOCK PARSER
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


def _is_xhr(request: Request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _format_option(letter: str, text: str) -> str:
    letter = (letter or "").strip().upper()
    text = (text or "").strip()
    if letter in ["A", "B", "C", "D"]:
        return f"{letter}. {text}"
    return text


exam_router = APIRouter(prefix="/admin/exams", tags=["Admin - Exams"])


# ==========================================================
# MANAGE EXAMS
# ==========================================================
@exam_router.get("/manage", response_class=HTMLResponse)
def exam_manage(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    exams = get_exams(db, user_id="admin", role="admin")
    return tpl.TemplateResponse("exams/manage.html", {"request": request, "exams": exams})


@exam_router.get("/create", response_class=HTMLResponse)
def exam_create_form(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    courses = db.query(Course).order_by(Course.course_name).all()
    return tpl.TemplateResponse("exams/create.html", {"request": request, "courses": courses})


@exam_router.post("/create")
def exam_create_post(
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
    from datetime import datetime
    try:
        af = datetime.fromisoformat(available_from) if available_from else None
        at = datetime.fromisoformat(available_to) if available_to else None
    except Exception:
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


@exam_router.get("/{exam_id}/edit", response_class=HTMLResponse)
def exam_edit_form(exam_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")
    courses = db.query(Course).order_by(Course.course_name).all()
    return tpl.TemplateResponse("exams/edit.html", {"request": request, "exam": exam, "courses": courses})


@exam_router.post("/{exam_id}/edit")
def exam_edit_post(
    exam_id: str, request: Request, db: Session = Depends(get_db),
    title: str = Form(...), description: str = Form(""),
    total_questions: int = Form(...),
    time_limit: int = Form(...),
    max_attempts: int = Form(...),
    passing_score: float = Form(...),
    available_from: str = Form(None),
    available_to: str = Form(None)
):
    from datetime import datetime
    try:
        af = datetime.fromisoformat(available_from) if available_from else None
        at = datetime.fromisoformat(available_to) if available_to else None
    except Exception:
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


@exam_router.get("/{exam_id}/delete")
def exam_delete(exam_id: str, db: Session = Depends(get_db)):
    try:
        delete_exam(db, "admin", "admin", exam_id)
    except Exception as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/admin/exams/manage", 303)


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
# IMPORT – GET
# ==========================================================
@exam_router.get("/{exam_id}/import", response_class=HTMLResponse)
def exam_import_form(exam_id: str, request: Request, db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/import.html", {"request": request, "exam": exam, "exam_id": exam_id})


# ==========================================================
# ✅ IMPORT – POST (FAST: BULK INSERT + BATCH COMMIT)
# ==========================================================
@exam_router.post("/{exam_id}/import")
async def exam_import_submit(
    exam_id: str,
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...)
):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")

    # đếm trước để cập nhật total_questions nhanh (khỏi count lại sau import)
    before_count = db.query(Question).filter(Question.quiz_id == exam_id).count()

    try:
        content = await file.read()
        filename = (file.filename or "").lower()
        df = None

        if filename.endswith(".xlsx"):
            # đọc theo header trước
            df_try = pd.read_excel(
                io.BytesIO(content),
                header=0,
                dtype=str,
                keep_default_na=False
            ).fillna("")
            df_try.columns = [str(c).strip().lower() for c in df_try.columns]

            needed = {"question_text", "option_a", "option_b", "option_c", "option_d", "correct"}
            if needed.issubset(set(df_try.columns)):
                df = df_try
            else:
                # fallback block/vertical
                temp_df = pd.read_excel(
                    io.BytesIO(content),
                    header=None,
                    dtype=str,
                    keep_default_na=False
                ).fillna("")
                blocks, buf = [], []
                for _, row in temp_df.iterrows():
                    line = str(row.iloc[0]).strip()
                    if not line or line.lower() == "nan":
                        if buf:
                            blocks.append("\n".join(buf))
                            buf = []
                        continue
                    buf.append(line)
                if buf:
                    blocks.append("\n".join(buf))

                df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        elif filename.endswith(".csv"):
            text = content.decode("utf-8-sig", errors="ignore")
            delimiters = [",", ";", "|", "\t"]
            for d in delimiters:
                try:
                    test = pd.read_csv(
                        io.StringIO(text),
                        delimiter=d,
                        dtype=str,
                        keep_default_na=False,
                        engine="python"
                    ).fillna("")
                    if test.shape[1] >= 1:
                        df = test
                        break
                except Exception:
                    continue

            if df is None:
                raise HTTPException(400, "Không đọc được CSV (delimiter không hợp lệ).")

            df.columns = [str(c).strip().lower() for c in df.columns]

            # CSV 2-column block
            if df.shape[1] == 2:
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

            else:
                needed = {"question_text", "option_a", "option_b", "option_c", "option_d", "correct"}
                if not needed.issubset(set(df.columns)):
                    blocks = [b for b in text.split("\n\n") if b.strip()]
                    df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        elif filename.endswith(".txt"):
            text = content.decode("utf-8-sig", errors="ignore").strip()

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
            if not blocks:
                blocks = [b for b in re.split(r"\r?\n\r?\n+", text) if b.strip()]
            df = pd.DataFrame([normalize_question_block(b) for b in blocks])

        else:
            raise HTTPException(400, "Chỉ hỗ trợ .xlsx / .csv / .txt")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Lỗi đọc file: {e}")

    if df is None or df.empty:
        raise HTTPException(400, "Không có dữ liệu để import.")

    # chuẩn hóa cột
    rename_map = {
        "question": "question_text",
        "title": "question_text",
        "description": "question_text",
        "a": "option_a", "b": "option_b", "c": "option_c", "d": "option_d",
        "answer": "correct",
        "correct": "correct",
    }

    df.columns = [str(c).strip().lower() for c in df.columns]
    df.rename(columns={c: rename_map.get(c, c) for c in df.columns}, inplace=True)
    df = df.fillna("")

    required = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct"]
    missing_cols = set(required) - set(df.columns)
    if missing_cols:
        raise HTTPException(400, f"Thiếu cột: {missing_cols}")

    # lấy đúng thứ tự cột để itertuples(name=None) chạy nhanh
    df = df[required]

    inserted = 0
    BATCH_Q = 200  # batch lớn hơn -> nhanh hơn (tùy DB bạn có thể chỉnh 200-500)
    q_batch = []
    opt_batch = []

    def _flush_batch():
        nonlocal q_batch, opt_batch
        if not q_batch:
            return
        # bulk insert cực nhanh
        db.bulk_save_objects(q_batch, return_defaults=False)
        db.bulk_save_objects(opt_batch, return_defaults=False)
        db.commit()
        q_batch.clear()
        opt_batch.clear()

    try:
        for (q_text, a, b, c, d, corr) in df.itertuples(index=False, name=None):
            q_text = str(q_text or "").strip()
            if not q_text:
                continue

            raw_correct = str(corr or "").strip().upper()
            correct_letter = next((ch for ch in raw_correct if ch in "ABCD"), None)
            if not correct_letter:
                continue

            qid = str(uuid.uuid4())
            q_batch.append(Question(
                id=qid,
                quiz_id=exam_id,
                question_text=q_text,
                difficulty_level=exam.difficulty_level
            ))

            options = {
                "A": str(a or "").strip(),
                "B": str(b or "").strip(),
                "C": str(c or "").strip(),
                "D": str(d or "").strip(),
            }

            for letter, text in options.items():
                opt_batch.append(QuestionOption(
                    id=str(uuid.uuid4()),
                    question_id=qid,
                    option_text=_format_option(letter, text),
                    is_correct=(letter == correct_letter)
                ))

            inserted += 1
            if inserted % BATCH_Q == 0:
                _flush_batch()

        # flush còn lại
        _flush_batch()

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Lỗi lưu DB: {e}")

    # ✅ cập nhật total_questions nhanh (khỏi count lại)
    new_total = before_count + inserted
    update_question_count(db, exam_id, new_total=new_total, commit=True)

    if _is_xhr(request):
        return JSONResponse({
            "ok": True,
            "inserted": inserted,
            "redirect": f"/admin/exams/{exam_id}/edit"
        })

    return RedirectResponse(f"/admin/exams/{exam_id}/edit", 303)


# ==========================================================
# QUESTION MANAGEMENT
# ==========================================================
@exam_router.get("/{exam_id}/questions", response_class=HTMLResponse)
def exam_question_list(exam_id: str, request: Request, db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")
    questions = get_questions_by_exam(db, exam_id)
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/questions/list.html", {"request": request, "exam": exam, "questions": questions})


@exam_router.get("/{exam_id}/questions/add", response_class=HTMLResponse)
def question_add_form(exam_id: str, request: Request, db: Session = Depends(get_db)):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Không tìm thấy kỳ thi.")
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("exams/questions/add.html", {"request": request, "exam": exam})


@exam_router.post("/{exam_id}/questions/add")
def question_add_post(
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
        create_question(db, exam_id, question_text, option_a, option_b, option_c, option_d, correct)
    except Exception as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)


@exam_router.get("/{exam_id}/questions/{question_id}/edit", response_class=HTMLResponse)
def question_edit_form(exam_id: str, question_id: str, request: Request, db: Session = Depends(get_db)):
    q = get_question(db, question_id)
    if not q:
        raise HTTPException(404, "Không tìm thấy câu hỏi.")

    options = db.query(QuestionOption).filter(QuestionOption.question_id == question_id).all()
    option_dict = {"A": "", "B": "", "C": "", "D": ""}
    correct_letter = ""

    for opt in options:
        raw = (opt.option_text or "").strip()
        if not raw:
            continue

        m = re.match(r"^\s*([A-Da-d])\s*[\)\.\:\-]\s*(.*)$", raw)
        if m:
            letter = m.group(1).upper()
            text = m.group(2).strip()
        else:
            letter = raw[0].upper() if raw else ""
            text = raw[2:].strip() if len(raw) > 2 and raw[1] in [")", "."] else raw

        if letter in option_dict and not option_dict[letter]:
            option_dict[letter] = text
        if opt.is_correct:
            correct_letter = letter if letter in "ABCD" else correct_letter

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


@exam_router.post("/{exam_id}/questions/{question_id}/edit")
def question_edit_post(
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
        update_question(db, question_id, question_text, option_a, option_b, option_c, option_d, correct)
    except Exception as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)


@exam_router.get("/{exam_id}/questions/{question_id}/delete")
def question_delete_route(exam_id: str, question_id: str, db: Session = Depends(get_db)):
    try:
        delete_question(db, question_id)
    except Exception as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(f"/admin/exams/{exam_id}/questions", 303)
