"""
👩‍🏫 app.services.teacher
Gói chứa các service dành riêng cho Giảng viên (Teacher).
"""

# =====================================================
# 📘 IMPORT CÁC SERVICE GIẢNG VIÊN
# =====================================================
from app.services.teacher.material_service import *

from app.services.teacher.course_section_service import *
from app.services.teacher.module_service import *
from app.services.teacher.lesson_service import *


# =====================================================
# 🧩 EXPORT RÕ RÀNG
# =====================================================
__all__ = [
    "material_service",

    "module_service",
    "lesson_service",

]
