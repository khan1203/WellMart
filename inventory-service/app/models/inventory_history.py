from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.database import Base


class InventoryHistory(Base):
    __tablename__ = "inventory_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True, nullable=False)
    quantity_change = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    change_type = Column(String, nullable=False)  # "add", "remove", "reserve", "release"
    reference_id = Column(String, nullable=True)  # Order ID or other reference
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
