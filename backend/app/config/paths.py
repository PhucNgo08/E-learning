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
UPLOAD_MESSAGES = UPLOADS_BASE / "messages"                     # File đính kèm tin nhắn

# === 🧭 Đường dẫn public tương ứng (frontend)
PUBLIC_PATH = "/uploads"

# ✅ Hàm kiểm tra thư mục tồn tại
def verify_upload_paths():
    paths = [
        UPLOADS_BASE,
        UPLOAD_COURSE_THUMBNAILS,
        UPLOAD_AVATARS,
        UPLOAD_MATERIALS,
        UPLOAD_VIDEOS,
        UPLOAD_MESSAGES
    ]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("⚠️ Các thư mục sau chưa tồn tại:")
        for p in missing:
            print("  -", p)
    else:
        print("✅ Tất cả các thư mục upload đều tồn tại.")

# Gọi hàm này khi khởi động ứng dụng (chỉ kiểm tra, không tạo thêm)
if __name__ == "__main__":
    verify_upload_paths()
