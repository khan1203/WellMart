from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InventoryBase(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=0)
    reserved: int = Field(default=0, ge=0)
    available: int = Field(..., ge=0)


class InventoryCreate(InventoryBase):
    pass


class Inventory(InventoryBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
