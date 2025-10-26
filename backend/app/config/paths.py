from pathlib import Path

# =====================================================
# 📁 CẤU HÌNH ĐƯỜNG DẪN TẬP TIN (UPLOADS / STATIC)
# =====================================================

# 🏠 Gốc thư mục backend/app
BASE_DIR = Path(__file__).resolve().parent.parent

# === 🗂️ Thư mục gốc chứa file upload
UPLOADS_BASE = BASE_DIR / "uploads"

# === 📸 Các thư mục con cho từng loại nội dung
UPLOAD_COURSE_THUMBNAILS = UPLOADS_BASE / "course_thumbnails"   # Ảnh khóa học
UPLOAD_AVATARS = UPLOADS_BASE / "avatars"                       # Ảnh đại diện
UPLOAD_MATERIALS = UPLOADS_BASE / "materials"                   # Tài liệu khóa học
UPLOAD_VIDEOS = UPLOADS_BASE / "videos"                         # Video bài học
UPLOAD_MESSAGES = UPLOADS_BASE / "messages"                     # File đính kèm tin nhắn (nếu có)

# === 🔧 Tự động tạo nếu chưa tồn tại
for path in [
    UPLOADS_BASE,
    UPLOAD_COURSE_THUMBNAILS,
    UPLOAD_AVATARS,
    UPLOAD_MATERIALS,
    UPLOAD_VIDEOS,
    UPLOAD_MESSAGES
]:
    path.mkdir(parents=True, exist_ok=True)

# === 🧭 Đường dẫn public tương ứng (frontend)
PUBLIC_PATH = "/uploads"

# ✅ Ví dụ:
#   - Upload thật: app/uploads/avatars/avatar123.png
#   - Public URL:  /uploads/avatars/avatar123.png
