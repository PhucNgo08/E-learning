from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings

settings = Settings()
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ✅ HÀM get_db dùng để tạo session DB khi xử lý request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
