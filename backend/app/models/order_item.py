from sqlalchemy import Column, String, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=uuid_str)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    course = relationship("Course", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} course={self.course_id}>"
