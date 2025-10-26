"""
=========================================================
🔍 SCRIPT KIỂM TRA LỖI ĐƯỜNG DẪN STATIC/UPLOADS
Tác dụng:
  - Quét toàn bộ project để phát hiện file nào có "/static/uploads"
  - Giúp tránh bị sinh thêm thư mục static/uploads/... khi chạy FastAPI
=========================================================
"""

import os
from pathlib import Path

# ===============================================
# ⚙️ CẤU HÌNH
# ===============================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # lên 1 cấp khỏi backend/
SCAN_DIRS = [
    PROJECT_ROOT / "backend" / "app",
    PROJECT_ROOT / "frontend" / "react-app",
]
KEYWORDS = ["/static/uploads", "static/uploads", "\\static\\uploads"]

# ===============================================
# 🧮 HÀM QUÉT
# ===============================================
def scan_conflicts():
    print("=" * 80)
    print("🔍 QUÉT LỖI ĐƯỜNG DẪN STATIC/UPLOADS".center(80))
    print("=" * 80)

    found_files = []

    for base_dir in SCAN_DIRS:
        if not base_dir.exists():
            print(f"⚠️ Thư mục không tồn tại, bỏ qua: {base_dir}")
            continue

        for root, _, files in os.walk(base_dir):
            for filename in files:
                # chỉ quét file HTML, JS, CSS, PY
                if not filename.endswith((".html", ".js", ".css", ".py")):
                    continue
                file_path = Path(root) / filename
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    for keyword in KEYWORDS:
                        if keyword in text:
                            found_files.append(file_path)
                            break
                except Exception as e:
                    print(f"⚠️ Không đọc được file {file_path}: {e}")

    if not found_files:
        print("✅ Không phát hiện file nào chứa '/static/uploads'.")
    else:
        print(f"⚠️ Phát hiện {len(found_files)} file có lỗi đường dẫn:")
        for f in found_files:
            print(f"   • {f}")

        print("\n💡 Gợi ý sửa:")
        print("   - Thay '/static/uploads/...' → '/uploads/...'")
        print("   - Hoặc dùng {{ url_for('static', path='...') }} đúng cách (nếu thật sự trong static)")
    print("=" * 80)


if __name__ == "__main__":
    scan_conflicts()
