from fastapi import FastAPI
from app.api.routes import products
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection

app = FastAPI(
    title="Product Service",
    description="Product management microservice",
    version="1.0.0"
)

# Startup and shutdown events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
