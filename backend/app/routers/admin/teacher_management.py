import traceback

from fastapi import APIRouter, Request, Form, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.services.admin import teacher_service
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/admin/teachers",
    tags=["Admin - Teacher Management"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "👩‍🏫 Quản lý giáo viên",
        "active_page": "teachers",
        "roles": ["teacher", "teaching_assistant"],
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/list", response_class=HTMLResponse)
def list_teachers(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        teachers = teacher_service.get_all_teachers(db)
        return render_template(
            request,
            "teacher/list.html",
            {
                "teachers": teachers,
                "page_title": "👩‍🏫 Danh sách giáo viên",
            },
        )
    except Exception:
        print("\n❌ LỖI TẢI DANH SÁCH GIÁO VIÊN:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)


@router.get("/create", response_class=HTMLResponse)
def create_teacher_form(
    request: Request,
    current_user=Depends(get_current_admin),
):
    return render_template(
        request,
        "teacher/create.html",
        {
            "form_data": {
                "username": "",
                "email": "",
                "full_name": "",
                "role": "teacher",
            },
            "error_message": None,
            "page_title": "➕ Thêm giáo viên",
        },
    )


@router.post("/create", response_class=HTMLResponse)
def create_teacher(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("teacher"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    username = (username or "").strip()
    email = (email or "").strip()
    full_name = (full_name or "").strip()
    role = (role or "teacher").strip()

    form_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "role": role,
    }

    if not username:
        return render_template(
            request,
            "teacher/create.html",
            {
                "form_data": form_data,
                "error_message": "Tên đăng nhập không được để trống.",
                "page_title": "➕ Thêm giáo viên",
            },
            status_code=400,
        )

    if not email:
        return render_template(
            request,
            "teacher/create.html",
            {
                "form_data": form_data,
                "error_message": "Email không được để trống.",
                "page_title": "➕ Thêm giáo viên",
            },
            status_code=400,
        )

    if not full_name:
        return render_template(
            request,
            "teacher/create.html",
            {
                "form_data": form_data,
                "error_message": "Họ tên không được để trống.",
                "page_title": "➕ Thêm giáo viên",
            },
            status_code=400,
        )

    try:
        teacher_service.create_teacher(db, username, email, full_name, role)
        return RedirectResponse(url="/admin/teachers/list", status_code=303)
    except Exception as e:
        return render_template(
            request,
            "teacher/create.html",
            {
                "form_data": form_data,
                "error_message": f"Lỗi khi tạo giáo viên: {e}",
                "page_title": "➕ Thêm giáo viên",
            },
            status_code=500,
        )


@router.get("/edit/{teacher_id}", response_class=HTMLResponse)
def edit_teacher(
    request: Request,
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    teacher = teacher_service.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

    return render_template(
        request,
        "teacher/edit.html",
        {
            "teacher": teacher,
            "page_title": "✏️ Chỉnh sửa giáo viên",
        },
    )


@router.post("/edit/{teacher_id}", response_class=HTMLResponse)
def update_teacher(
    request: Request,
    teacher_id: str,
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    teacher = teacher_service.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

    full_name = (full_name or "").strip()
    email = (email or "").strip()
    role = (role or "").strip()

    if not full_name:
        teacher.full_name = full_name
        teacher.email = email
        teacher.role = role
        return render_template(
            request,
            "teacher/edit.html",
            {
                "teacher": teacher,
                "error_message": "Họ tên không được để trống.",
                "page_title": "✏️ Chỉnh sửa giáo viên",
            },
            status_code=400,
        )

    if not email:
        teacher.full_name = full_name
        teacher.email = email
        teacher.role = role
        return render_template(
            request,
            "teacher/edit.html",
            {
                "teacher": teacher,
                "error_message": "Email không được để trống.",
                "page_title": "✏️ Chỉnh sửa giáo viên",
            },
            status_code=400,
        )

    try:
        updated = teacher_service.update_teacher(db, teacher_id, full_name, email, role)
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

        return RedirectResponse(url="/admin/teachers/list", status_code=303)
    except HTTPException:
        raise
    except Exception as e:
        teacher.full_name = full_name
        teacher.email = email
        teacher.role = role
        return render_template(
            request,
            "teacher/edit.html",
            {
                "teacher": teacher,
                "error_message": f"Lỗi khi cập nhật giáo viên: {e}",
                "page_title": "✏️ Chỉnh sửa giáo viên",
            },
            status_code=500,
        )


@router.get("/avatar/{teacher_id}", response_class=HTMLResponse)
def edit_avatar(
    request: Request,
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    teacher = teacher_service.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

    return render_template(
        request,
        "teacher/edit_avatar.html",
        {
            "teacher": teacher,
            "page_title": "🖼️ Cập nhật Avatar",
        },
    )


@router.post("/avatar/{teacher_id}")
def upload_avatar(
    request: Request,
    teacher_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    teacher = teacher_service.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

    try:
        teacher_service.update_teacher_avatar(db, teacher_id, file)
        return RedirectResponse(url=f"/admin/teachers/edit/{teacher_id}", status_code=303)
    except Exception as e:
        return render_template(
            request,
            "teacher/edit_avatar.html",
            {
                "teacher": teacher,
                "error_message": f"Lỗi khi cập nhật avatar: {e}",
                "page_title": "🖼️ Cập nhật Avatar",
            },
            status_code=500,
        )


@router.get("/reset-password/{teacher_id}", response_class=HTMLResponse)
def reset_password(
    request: Request,
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Giữ GET để tương thích template hiện tại của bạn.
    Nếu muốn chặt hơn về bảo mật, nên tách thành GET xác nhận + POST thực thi.
    """
    teacher = teacher_service.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên")

    try:
        teacher, new_pwd = teacher_service.reset_teacher_password(db, teacher_id)
        return render_template(
            request,
            "teacher/reset_password.html",
            {
                "teacher": teacher,
                "new_password": new_pwd,
                "page_title": "🔐 Mật khẩu mới",
            },
        )
    except Exception as e:
        return render_template(
            request,
            "teacher/reset_password.html",
            {
                "teacher": teacher,
                "new_password": None,
                "error_message": f"Lỗi khi reset mật khẩu: {e}",
                "page_title": "🔐 Mật khẩu mới",
            },
            status_code=500,
        )