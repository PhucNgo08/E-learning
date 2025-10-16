from app.database.connection import Base
from app.db.session import engine   
import sys
import os
# Thêm đường dẫn gốc của project vào sys.path để Python hiểu được app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.db.session import engine



def init_db():
    print("🔧 Đang tạo bảng từ các model...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tạo bảng thành công.")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
    else:
        print("Sử dụng: python init.py init để khởi tạo cơ sở dữ liệu.")