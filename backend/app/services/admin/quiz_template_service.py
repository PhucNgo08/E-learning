from sqlalchemy.orm import Session
from app.models.quiz_template import QuizTemplate
from datetime import datetime
import uuid

# ============================================================
# 📌 Lấy tất cả Template
# ============================================================
def get_all(db: Session):
    return (
        db.query(QuizTemplate)
        .order_by(QuizTemplate.created_at.desc())
        .all()
    )


# ============================================================
# 📌 Lấy tất cả Template kèm thông tin người tạo
# ============================================================
def get_all_with_creator(db: Session):
    return (
        db.query(QuizTemplate)
        .join(QuizTemplate.creator)       # 🔥 JOIN đúng quan hệ
        .order_by(QuizTemplate.created_at.desc())
        .all()
    )


# ============================================================
# 📌 Lấy template theo ID
# ============================================================
def get_by_id(db: Session, template_id: str):
    return db.query(QuizTemplate).filter(QuizTemplate.id == template_id).first()


# ============================================================
# 📌 Tạo template mới
# ============================================================
def create(db: Session, name: str, description: str, rules: str, created_by: str):
    qt = QuizTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        rules=rules,
        created_by=created_by,
        is_public=0,
        created_at=datetime.utcnow()
    )

    db.add(qt)
    db.commit()
    db.refresh(qt)
    return qt


# ============================================================
# 📌 Update Template
# ============================================================
def update(db: Session, template_id: str, name: str, description: str, rules: str):
    qt = get_by_id(db, template_id)
    if not qt:
        return None

    qt.name = name
    qt.description = description
    qt.rules = rules
    qt.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(qt)
    return qt


# ============================================================
# 📌 Delete Template
# ============================================================
def delete(db: Session, template_id: str):
    qt = get_by_id(db, template_id)
    if not qt:
        return False

    db.delete(qt)
    db.commit()
    return True
