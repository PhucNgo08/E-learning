# app/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import quote_plus 
import os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "e_learning")

encoded_password = quote_plus(DB_PASS)

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  
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
