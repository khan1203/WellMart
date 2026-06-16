from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "order_db"
    USER_SERVICE_URL: str = "http://user-service:8000"
    PRODUCT_SERVICE_URL: str = "http://product-service:8001"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8002"

    class Config:
        env_file = ".env"


settings = Settings()
