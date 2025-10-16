from fastapi import APIRouter
from app.routers.admin.course_management import course_router
from app.routers.admin.user_management import user_router
from app.routers.admin.class_management import class_router
from app.routers.admin.enrollment_management import enrollment_router
from app.routers.admin.exam_management import exam_router
from app.routers.admin.backup_management import backup_router

from app.routers.admin.report_management import report_router

admin_router = APIRouter()

# Include all the admin routes here
admin_router.include_router(course_router, prefix="/course", tags=["Course Management"])
admin_router.include_router(user_router, prefix="/user", tags=["User Management"])
admin_router.include_router(class_router, prefix="/class", tags=["Class Management"])
admin_router.include_router(enrollment_router, prefix="/enrollment", tags=["Enrollment Management"])
admin_router.include_router(exam_router, prefix="/exam", tags=["Exam Management"])
admin_router.include_router(backup_router, prefix="/backup", tags=["Backup Management"])
admin_router.include_router(report_router, prefix="/report", tags=["Report Management"])
