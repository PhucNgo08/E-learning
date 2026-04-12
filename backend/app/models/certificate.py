import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_code = Column(String(50), unique=True, nullable=False)
    issued_at = Column(DateTime, server_default=func.now(), nullable=False)
    certificate_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="issued")

    user = relationship("User", back_populates="certificates")
    course = relationship("Course")

    def __repr__(self) -> str:
        return (
            f"<Certificate(certificate_code='{self.certificate_code}', "
            f"status='{self.status}')>"
        )