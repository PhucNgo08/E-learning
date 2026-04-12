from sqlalchemy.orm import Query
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.student_profile import StudentProfile
from app.models.teacher_profiles import TeacherProfile
from app.models.rbac import Role


def join_user_profile(query: Query) -> Query:
    return query.outerjoin(UserProfile, UserProfile.user_id == User.id)


def join_student_profile(query: Query) -> Query:
    return query.outerjoin(StudentProfile, StudentProfile.user_id == User.id)


def join_teacher_profile(query: Query) -> Query:
    return query.outerjoin(TeacherProfile, TeacherProfile.user_id == User.id)


def join_user_roles(query: Query) -> Query:
    return query.outerjoin(User.roles)


def filter_users_by_role(query: Query, role_code: str) -> Query:
    return query.join(User.roles).filter(Role.role_code == role_code)


def order_users_by_full_name(query: Query) -> Query:
    return query.outerjoin(UserProfile, UserProfile.user_id == User.id).order_by(UserProfile.full_name.asc())