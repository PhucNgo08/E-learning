from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.dependencies.auth import get_current_student
from app.services.wallet_service import get_balance

def student_common(
    db: Session = Depends(get_db),
    student = Depends(get_current_student)
):
    balance = get_balance(db, student.id)
    return {"student": student, "balance": balance}
