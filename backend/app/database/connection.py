# app/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ Địa chỉ kết nối MySQL (sửa đúng)
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:111004%40@localhost:3309/e_learning"
# Nếu mật khẩu MySQL KHÔNG có ký tự đặc biệt, ví dụ 111004123 thì dùng:
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:111004123@localhost:3309/e_learning"

# ✅ Khởi tạo engine (sử dụng đúng biến)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # giúp tránh lỗi "MySQL server has gone away"
)

# ✅ Tạo đối tượng base cho ORM models
Base = declarative_base()

# ✅ Khởi tạo session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Hàm tạo phiên DB cho route FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
