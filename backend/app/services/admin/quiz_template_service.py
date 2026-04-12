"""
==========================================================
📘 SERVICE: Quiz Template Management
CRUD cho mẫu đề quiz
==========================================================
"""
from datetime import datetime
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.quiz_template import QuizTemplate


def get_all(db: Session) -> list[QuizTemplate]:
    return (
        db.query(QuizTemplate)
        .order_by(QuizTemplate.created_at.desc())
        .all()
    )


def get_all_with_creator(db: Session) -> list[QuizTemplate]:
    query = db.query(QuizTemplate)

    # Nếu model có relationship "creator" thì preload luôn
    if hasattr(QuizTemplate, "creator"):
        query = query.options(joinedload(QuizTemplate.creator))

    return query.order_by(QuizTemplate.created_at.desc()).all()


def get_by_id(db: Session, template_id: str) -> QuizTemplate | None:
    query = db.query(QuizTemplate)

    if hasattr(QuizTemplate, "creator"):
        query = query.options(joinedload(QuizTemplate.creator))

    return query.filter(QuizTemplate.id == template_id).first()


def create(
    db: Session,
    name: str,
    description: str,
    rules: str,
    created_by: str,
) -> QuizTemplate:
    name = (name or "").strip()
    description = (description or "").strip() or None
    rules = (rules or "").strip()

    qt = QuizTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        rules=rules,
        created_by=created_by,
        is_public=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(qt)
        db.commit()
        db.refresh(qt)
        return qt
    except SQLAlchemyError:
        db.rollback()
        raise


def update(
    db: Session,
    template_id: str,
    name: str,
    description: str,
    rules: str,
) -> QuizTemplate | None:
    qt = get_by_id(db, template_id)
    if not qt:
        return None

    qt.name = (name or "").strip()
    qt.description = (description or "").strip() or None
    qt.rules = (rules or "").strip()
    qt.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(qt)
        return qt
    except SQLAlchemyError:
        db.rollback()
        raise


def delete(db: Session, template_id: str) -> bool:
    qt = get_by_id(db, template_id)
    if not qt:
        return False

    try:
        db.delete(qt)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise