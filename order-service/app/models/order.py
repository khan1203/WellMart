from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Address(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str


class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)


class OrderCreate(BaseModel):
    user_id: str
    items: List[OrderItem]
    shipping_address: Address


class Order(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    items: List[dict]
    total_price: float
    status: str
    shipping_address: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class StatusUpdate(BaseModel):
    status: OrderStatus
