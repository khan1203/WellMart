from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.models.inventory_item import InventoryItem
from app.models.inventory_history import InventoryHistory

router = APIRouter()


# Pydantic schemas
class InventoryItemCreate(BaseModel):
    product_id: str
    available_quantity: int = 0
    reorder_threshold: int = 5


class InventoryItemUpdate(BaseModel):
    available_quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    reorder_threshold: Optional[int] = None


class InventoryItemResponse(BaseModel):
    id: int
    product_id: str
    available_quantity: int
    reserved_quantity: int
    reorder_threshold: int

    class Config:
        from_attributes = True


class InventoryCheck(BaseModel):
    product_id: str
    quantity: int


class ReserveRequest(BaseModel):
    product_id: str
    quantity: int
    reference_id: Optional[str] = None


class ReleaseRequest(BaseModel):
    product_id: str
    quantity: int
    reference_id: Optional[str] = None


class AdjustRequest(BaseModel):
    product_id: str
    quantity_change: int
    reason: Optional[str] = None


class HistoryResponse(BaseModel):
    id: int
    product_id: str
    quantity_change: int
    previous_quantity: int
    new_quantity: int
    change_type: str
    reference_id: Optional[str]
    timestamp: str

    class Config:
        from_attributes = True


def log_history(
    db: Session,
    product_id: str,
    quantity_change: int,
    previous_quantity: int,
    new_quantity: int,
    change_type: str,
    reference_id: Optional[str] = None
):
    """Log inventory change to history."""
    history = InventoryHistory(
        product_id=product_id,
        quantity_change=quantity_change,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        change_type=change_type,
        reference_id=reference_id
    )
    db.add(history)


@router.post("/", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    item_data: InventoryItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new inventory record for a product with validation and history tracking."""
    # Check if inventory already exists
    existing = db.query(InventoryItem).filter(InventoryItem.product_id == item_data.product_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory record already exists for this product"
        )

    if item_data.available_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Available quantity cannot be negative"
        )

    item = InventoryItem(
        product_id=item_data.product_id,
        available_quantity=item_data.available_quantity,
        reserved_quantity=0,
        reorder_threshold=item_data.reorder_threshold
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Log initial inventory
    log_history(
        db=db,
        product_id=item.product_id,
        quantity_change=item.available_quantity,
        previous_quantity=0,
        new_quantity=item.available_quantity,
        change_type="add"
    )
    db.commit()

    return item


@router.get("/", response_model=List[InventoryItemResponse])
def list_inventory(
    low_stock: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List inventory items with support for filtering and pagination."""
    query = db.query(InventoryItem)

    if low_stock:
        query = query.filter(InventoryItem.available_quantity <= InventoryItem.reorder_threshold)

    skip = (page - 1) * limit
    items = query.offset(skip).limit(limit).all()
    return items


@router.get("/check")
def check_inventory(
    product_id: str,
    quantity: int,
    db: Session = Depends(get_db)
):
    """Check if a product has sufficient inventory for a requested quantity."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product inventory not found"
        )

    sufficient = item.available_quantity >= quantity
    return {
        "product_id": product_id,
        "requested": quantity,
        "available": item.available_quantity,
        "sufficient": sufficient
    }


@router.get("/{product_id}", response_model=InventoryItemResponse)
def get_inventory(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve full inventory details for a specific product."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    return item


@router.put("/{product_id}", response_model=InventoryItemResponse)
def update_inventory(
    product_id: str,
    update_data: InventoryItemUpdate,
    db: Session = Depends(get_db)
):
    """Update inventory quantities and settings with automatic logging."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    # Track changes for history
    prev_available = item.available_quantity

    if update_data.available_quantity is not None:
        if update_data.available_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Available quantity cannot be negative"
            )
        item.available_quantity = update_data.available_quantity

    if update_data.reserved_quantity is not None:
        if update_data.reserved_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reserved quantity cannot be negative"
            )
        item.reserved_quantity = update_data.reserved_quantity

    if update_data.reorder_threshold is not None:
        item.reorder_threshold = update_data.reorder_threshold

    db.commit()
    db.refresh(item)

    # Log the change
    if prev_available != item.available_quantity:
        log_history(
            db=db,
            product_id=product_id,
            quantity_change=item.available_quantity - prev_available,
            previous_quantity=prev_available,
            new_quantity=item.available_quantity,
            change_type="adjust"
        )
        db.commit()

    return item


@router.post("/reserve")
def reserve_inventory(
    request: ReserveRequest,
    db: Session = Depends(get_db)
):
    """Reserve product inventory for order processing."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == request.product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    if item.available_quantity < request.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient inventory"
        )

    prev_available = item.available_quantity
    prev_reserved = item.reserved_quantity

    item.available_quantity -= request.quantity
    item.reserved_quantity += request.quantity

    db.commit()
    db.refresh(item)

    # Log the reservation
    log_history(
        db=db,
        product_id=request.product_id,
        quantity_change=-request.quantity,
        previous_quantity=prev_available,
        new_quantity=item.available_quantity,
        change_type="reserve",
        reference_id=request.reference_id
    )
    db.commit()

    return {
        "product_id": request.product_id,
        "reserved": request.quantity,
        "available": item.available_quantity,
        "reserved_total": item.reserved_quantity
    }


@router.post("/release")
def release_inventory(
    request: ReleaseRequest,
    db: Session = Depends(get_db)
):
    """Release previously reserved inventory back to available stock."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == request.product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    if item.reserved_quantity < request.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot release more than reserved"
        )

    prev_available = item.available_quantity
    prev_reserved = item.reserved_quantity

    item.available_quantity += request.quantity
    item.reserved_quantity -= request.quantity

    db.commit()
    db.refresh(item)

    # Log the release
    log_history(
        db=db,
        product_id=request.product_id,
        quantity_change=request.quantity,
        previous_quantity=prev_available,
        new_quantity=item.available_quantity,
        change_type="release",
        reference_id=request.reference_id
    )
    db.commit()

    return {
        "product_id": request.product_id,
        "released": request.quantity,
        "available": item.available_quantity,
        "reserved_total": item.reserved_quantity
    }


@router.post("/adjust")
def adjust_inventory(
    request: AdjustRequest,
    db: Session = Depends(get_db)
):
    """Perform manual inventory adjustments with reason tracking."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == request.product_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    new_quantity = item.available_quantity + request.quantity_change

    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment would result in negative quantity"
        )

    prev_available = item.available_quantity
    item.available_quantity = new_quantity

    db.commit()
    db.refresh(item)

    # Log the adjustment
    log_history(
        db=db,
        product_id=request.product_id,
        quantity_change=request.quantity_change,
        previous_quantity=prev_available,
        new_quantity=item.available_quantity,
        change_type="adjust",
        reference_id=request.reason
    )
    db.commit()

    return {
        "product_id": request.product_id,
        "adjustment": request.quantity_change,
        "new_available": item.available_quantity
    }


@router.get("/low-stock", response_model=List[InventoryItemResponse])
def get_low_stock(db: Session = Depends(get_db)):
    """Get a list of products that are below their reorder thresholds."""
    items = db.query(InventoryItem).filter(
        InventoryItem.available_quantity <= InventoryItem.reorder_threshold
    ).all()
    return items


@router.get("/history/{product_id}", response_model=List[HistoryResponse])
def get_inventory_history(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Fetch a product's full inventory change history."""
    history = db.query(InventoryHistory).filter(
        InventoryHistory.product_id == product_id
    ).order_by(InventoryHistory.timestamp.desc()).limit(limit).all()

    return [
        HistoryResponse(
            id=h.id,
            product_id=h.product_id,
            quantity_change=h.quantity_change,
            previous_quantity=h.previous_quantity,
            new_quantity=h.new_quantity,
            change_type=h.change_type,
            reference_id=h.reference_id,
            timestamp=h.timestamp.isoformat()
        )
        for h in history
    ]
