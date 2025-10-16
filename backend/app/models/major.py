from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base


class Major(Base):
    __tablename__ = "majors"

    # ===========================
    # 🧩 Cấu trúc bảng majors
    # ===========================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    major_code = Column(String(10), unique=True, nullable=False)       # Mã ngành
    major_name = Column(String(100), nullable=False)                   # Tên ngành
    faculty_name = Column(String(100))                                 # Khoa trực thuộc
    is_active = Column(Boolean, default=True)                          # Trạng thái hoạt động
    created_at = Column(DateTime, default=datetime.utcnow)             # Ngày tạo

    # ===========================
    # 🔗 Quan hệ ORM
    # ===========================
    users = relationship("User", back_populates="major", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="major")  
    courses = relationship("Course", back_populates="major", cascade="all, delete-orphan")

    # ===========================
    # 🧾 Hiển thị gọn trong console
    # ===========================
    def __repr__(self):
        return f"<Major(code='{self.major_code}', name='{self.major_name}', active={self.is_active})>"
