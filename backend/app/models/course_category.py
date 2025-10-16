# app/models/course_category.py

from sqlalchemy import Column, String, Text
from app.database.connection import Base

class CourseCategory(Base):
    __tablename__ = 'course_categories'

    # Các cột trong bảng course_categories
    id = Column(String(36), primary_key=True)
    category_name = Column(String(100), unique=True, nullable=False)  # Tên danh mục khóa học
    description = Column(Text, nullable=True)  # Mô tả danh mục khóa học (có thể để trống)

    def __repr__(self):
        return f"<CourseCategory(id={self.id}, category_name={self.category_name})>"
