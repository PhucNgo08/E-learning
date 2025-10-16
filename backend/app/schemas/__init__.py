# app/schemas/__init__.py

from .UserCreate import UserCreate, UserUpdate, UserResponse
from .enrollment import EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse
from .course import CourseCreate, CourseUpdate, CourseResponse
from .classes import ClassCreate, ClassUpdate, ClassResponse
from .login import LoginRequest
from .auth import AuthToken
