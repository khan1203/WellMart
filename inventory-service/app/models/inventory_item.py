from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint, func
from app.db.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, index=True, nullable=False)
    available_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('available_quantity >= 0', name='check_available_quantity_non_negative'),
        CheckConstraint('reserved_quantity >= 0', name='check_reserved_quantity_non_negative'),
    )
