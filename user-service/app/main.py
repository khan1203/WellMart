from fastapi import FastAPI
from app.api.routes import auth, users
from app.core.config import settings
from app.db.database import engine
from app.models import user, address

# Create database tables
user.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="User Service",
    description="User management and authentication microservice",
    version="1.0.0"
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
