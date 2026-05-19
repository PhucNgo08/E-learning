from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "assigned_at",
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    ),
)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        String(36),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=uuid_str)

    role_code = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    role_name = Column(
        String(100),
        nullable=False,
    )

    description = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(code='{self.role_code}', name='{self.role_name}')>"


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=uuid_str)

    permission_code = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    permission_name = Column(
        String(150),
        nullable=False,
    )

    description = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Permission("
            f"code='{self.permission_code}', "
            f"name='{self.permission_name}'"
            f")>"
        )