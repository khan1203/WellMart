from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "product_db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8002"

    class Config:
        env_file = ".env"


settings = Settings()
