from sqlalchemy.orm import Session
from app.models.quiz_template import QuizTemplate
from datetime import datetime
import uuid

def get_all(db: Session):
    return db.query(QuizTemplate).all()

def get_by_id(db: Session, template_id: str):
    return db.query(QuizTemplate).filter(QuizTemplate.id == template_id).first()

def create(db: Session, name, description, rules):
    qt = QuizTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        rules=rules,
        created_at=datetime.utcnow()
    )
    db.add(qt)
    db.commit()
    db.refresh(qt)
    return qt

def update(db: Session, template_id, name, description, rules):
    qt = get_by_id(db, template_id)
    if qt:
        qt.name = name
        qt.description = description
        qt.rules = rules
        qt.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(qt)
    return qt

def delete(db: Session, template_id):
    qt = get_by_id(db, template_id)
    if qt:
        db.delete(qt)
        db.commit()
