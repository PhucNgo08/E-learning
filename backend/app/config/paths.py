from __future__ import annotations

from pathlib import Path

# =====================================================
# 📁 CẤU HÌNH ĐƯỜNG DẪN TẬP TIN (UPLOADS / STATIC)
# =====================================================

# 🏠 Gốc thư mục backend/app
BASE_DIR = Path(__file__).resolve().parent.parent

# === 🗂️ Thư mục gốc chứa file upload
UPLOADS_BASE = BASE_DIR / "uploads"
PUBLIC_PATH = "/uploads"

# === 📸 Các thư mục con cho từng loại nội dung
UPLOAD_COURSE_THUMBNAILS = UPLOADS_BASE / "course_thumbnails"
UPLOAD_AVATARS = UPLOADS_BASE / "avatars"
UPLOAD_MATERIALS = UPLOADS_BASE / "materials"
UPLOAD_VIDEOS = UPLOADS_BASE / "videos"
UPLOAD_MESSAGES = UPLOADS_BASE / "messages"
UPLOAD_DOCUMENTS = UPLOADS_BASE / "documents"

UPLOAD_DIRS = {
    "course_thumbnails": UPLOAD_COURSE_THUMBNAILS,
    "avatars": UPLOAD_AVATARS,
    "materials": UPLOAD_MATERIALS,
    "videos": UPLOAD_VIDEOS,
    "messages": UPLOAD_MESSAGES,
    "documents": UPLOAD_DOCUMENTS,
}


def ensure_upload_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_upload_dir(subdir: str) -> Path:
    if subdir not in UPLOAD_DIRS:
        raise ValueError(f"Unknown upload subdir: {subdir}")
    return ensure_upload_dir(UPLOAD_DIRS[subdir])


def build_upload_url(subdir: str, filename: str) -> str:
    filename = (filename or "").strip().lstrip("/\\")
    if not filename:
        raise ValueError("filename is required")
    return f"{PUBLIC_PATH}/{subdir}/{filename}"


def resolve_upload_path_from_url(file_url: str | None) -> Path | None:
    if not file_url:
        return None

    clean = str(file_url).strip()
    if not clean:
        return None

    if clean.startswith(PUBLIC_PATH + "/"):
        relative = clean[len(PUBLIC_PATH) + 1 :]
        return UPLOADS_BASE / relative

    candidate = Path(clean)
    if candidate.is_absolute():
        return candidate

    if candidate.parts and candidate.parts[0] == "uploads":
        return UPLOADS_BASE / Path(*candidate.parts[1:])

    return UPLOADS_BASE / candidate


def verify_upload_paths(create_missing: bool = False):
    paths = [UPLOADS_BASE, *UPLOAD_DIRS.values()]

    if create_missing:
        for p in paths:
            p.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("⚠️ Các thư mục sau chưa tồn tại:")
        for p in missing:
            print("  -", p)
    else:
        print("✅ Tất cả các thư mục upload đều tồn tại.")


if __name__ == "__main__":
    verify_upload_paths(create_missing=True)