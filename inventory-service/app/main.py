from fastapi import FastAPI
from app.api.routes import inventory
from app.core.config import settings
from app.db.database import engine
from app.models import inventory_item, inventory_history

# Create database tables
inventory_item.Base.metadata.create_all(bind=engine)
inventory_history.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Inventory Service",
    description="Inventory management microservice",
    version="1.0.0"
)

# Include routers
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
