from pathlib import Path

# === Đường dẫn gốc dự án (backend/app)
BASE_DIR = Path(__file__).resolve().parent.parent

# === Uploads
UPLOADS_BASE = BASE_DIR / "uploads"

# Từng thư mục con
UPLOAD_COURSE_THUMBNAILS = UPLOADS_BASE / "course_thumbnails"
UPLOAD_AVATARS = UPLOADS_BASE / "avatars"
UPLOAD_MATERIALS = UPLOADS_BASE / "materials"
UPLOAD_VIDEOS = UPLOADS_BASE / "videos"

# Tạo thư mục nếu chưa có
for path in [UPLOADS_BASE, UPLOAD_COURSE_THUMBNAILS, UPLOAD_AVATARS, UPLOAD_MATERIALS, UPLOAD_VIDEOS]:
    path.mkdir(parents=True, exist_ok=True)
