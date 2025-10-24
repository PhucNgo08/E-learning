"""
=====================================================
📦 app/services/__init__.py
Gọn gàng - tránh vòng import
=====================================================
"""

# Chỉ khai báo package, không import module con tại đây.
# Khi cần dùng service, hãy import trực tiếp từ nhánh con:
#   from app.services.admin import course_service
#   from app.services.teacher import lesson_service
#   from app.services.common import auth_service
#
# Không cần alias import để tránh circular import.

__all__ = []
