from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.database import get_db
from app.models.product import ProductCreate, ProductUpdate, Product
from app.models.inventory import InventoryCreate
from app.services.inventory_service import InventoryService

router = APIRouter()


def serialize_product(product: dict) -> dict:
    """Convert MongoDB document to API response."""
    if product:
        product["_id"] = str(product["_id"])
    return product


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new product and auto-generate its inventory record."""
    product_doc = {
        "name": product_data.name,
        "description": product_data.description,
        "category": product_data.category,
        "price": product_data.price,
        "quantity": product_data.quantity,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.products.insert_one(product_doc)
    product_doc["_id"] = result.inserted_id

    # Auto-create inventory record in Inventory Service
    inventory_service = InventoryService()
    await inventory_service.create_inventory(
        product_id=str(result.inserted_id),
        quantity=product_data.quantity
    )

    return serialize_product(product_doc)


@router.get("/", response_model=List[Product])
async def list_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieve a filtered and paginated list of products."""
    query = {}

    if category:
        query["category"] = category
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price

    skip = (page - 1) * limit
    cursor = db.products.find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)

    return [serialize_product(p) for p in products]


@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get detailed information for a single product by ID."""
    try:
        product = await db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return serialize_product(product)


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Partially update product details by ID."""
    try:
        existing_product = await db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    update_data = product_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()

    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
    return serialize_product(updated_product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Delete a product by ID."""
    try:
        result = await db.products.delete_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Also delete the associated inventory
    await db.inventory.delete_one({"product_id": product_id})

    return None


@router.get("/category/list")
async def list_categories(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Retrieve a list of all unique product categories."""
    categories = await db.products.distinct("category")
    return {"categories": categories}
