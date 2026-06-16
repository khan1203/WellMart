from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.database import get_db
from app.models.order import OrderCreate, Order, OrderStatus, StatusUpdate
from app.services.user_service import UserServiceClient, ProductServiceClient, InventoryServiceClient

router = APIRouter()

# Service clients
user_client = UserServiceClient()
product_client = ProductServiceClient()
inventory_client = InventoryServiceClient()


def serialize_order(order: dict) -> dict:
    """Convert MongoDB document to API response."""
    if order:
        order["_id"] = str(order["_id"])
    return order


@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new order with full validation, inventory reservation, and rollback on failure."""
    # Verify user exists
    try:
        user_id_int = int(order_data.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user_exists = await user_client.verify_user(user_id_int)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate items and calculate total
    total_price = 0.0
    items_data = []

    for item in order_data.items:
        # Get product details
        product = await product_client.get_product(item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} not found"
            )

        # Check inventory availability
        inventory_check = await inventory_client.check_availability(item.product_id, item.quantity)
        if not inventory_check or not inventory_check.get("sufficient"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory for product {item.product_id}"
            )

        # Use product price at time of order
        item_total = product["price"] * item.quantity
        total_price += item_total

        items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": product["price"]
        })

    # Generate order ID for reference
    order_id = str(ObjectId())

    # Reserve inventory for all items
    reserved_items = []
    for item in order_data.items:
        success = await inventory_client.reserve(item.product_id, item.quantity, order_id)
        if not success:
            # Rollback: release previously reserved items
            for reserved_item in reserved_items:
                await inventory_client.release(
                    reserved_item["product_id"],
                    reserved_item["quantity"],
                    order_id
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reserve inventory"
            )
        reserved_items.append({"product_id": item.product_id, "quantity": item.quantity})

    # Create order document
    order_doc = {
        "user_id": order_data.user_id,
        "items": items_data,
        "total_price": total_price,
        "status": OrderStatus.PENDING.value,
        "shipping_address": order_data.shipping_address.model_dump(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.orders.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id

    return serialize_order(order_doc)


@router.get("/", response_model=List[Order])
async def list_orders(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieve paginated list of orders with filtering by status, user, and date range."""
    query = {}

    if status:
        query["status"] = status
    if user_id:
        query["user_id"] = user_id

    if start_date or end_date:
        query["created_at"] = {}
        if start_date:
            query["created_at"]["$gte"] = start_date
        if end_date:
            query["created_at"]["$lte"] = end_date

    skip = (page - 1) * limit
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return [serialize_order(o) for o in orders]


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Fetch detailed information for a specific order by its ID."""
    try:
        order = await db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return serialize_order(order)


@router.get("/user/{user_id}", response_model=List[Order])
async def get_user_orders(
    user_id: str,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all orders for a specific user with status filtering and pagination."""
    query = {"user_id": user_id}

    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return [serialize_order(o) for o in orders]


@router.put("/{order_id}/status", response_model=Order)
async def update_order_status(
    order_id: str,
    status_update: StatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update an order's status with validation and inventory impact handling."""
    try:
        order = await db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    old_status = order["status"]
    new_status = status_update.status.value

    # Validate status transition
    valid_transitions = {
        OrderStatus.PENDING.value: [OrderStatus.PAID.value, OrderStatus.CANCELLED.value],
        OrderStatus.PAID.value: [OrderStatus.PROCESSING.value, OrderStatus.CANCELLED.value],
        OrderStatus.PROCESSING.value: [OrderStatus.SHIPPED.value],
        OrderStatus.SHIPPED.value: [OrderStatus.DELIVERED.value],
        OrderStatus.DELIVERED.value: [],
        OrderStatus.CANCELLED.value: [],
    }

    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {old_status} to {new_status}"
        )

    # Handle inventory impact
    if new_status == OrderStatus.CANCELLED.value and old_status != OrderStatus.CANCELLED.value:
        # Release reserved inventory
        for item in order["items"]:
            await inventory_client.release(
                item["product_id"],
                item["quantity"],
                order_id
            )

    # Update order
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
    )

    updated_order = await db.orders.find_one({"_id": ObjectId(order_id)})
    return serialize_order(updated_order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Cancel an order if eligible and automatically release reserved inventory."""
    try:
        order = await db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Only pending or paid orders can be cancelled
    if order["status"] not in [OrderStatus.PENDING.value, OrderStatus.PAID.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled in current status"
        )

    # Release reserved inventory
    for item in order["items"]:
        await inventory_client.release(
            item["product_id"],
            item["quantity"],
            order_id
        )

    # Update order status to cancelled
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": OrderStatus.CANCELLED.value, "updated_at": datetime.utcnow()}}
    )

    return None
