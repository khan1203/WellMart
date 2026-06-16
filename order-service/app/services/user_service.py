import httpx
from app.core.config import settings


class UserServiceClient:
    def __init__(self):
        self.base_url = settings.USER_SERVICE_URL

    async def verify_user(self, user_id: int) -> bool:
        """Verify if a user exists."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/users/{user_id}/verify")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("exists", False)
                return False
            except Exception:
                return False


class ProductServiceClient:
    def __init__(self):
        self.base_url = settings.PRODUCT_SERVICE_URL

    async def get_product(self, product_id: str) -> dict | None:
        """Get product details."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/products/{product_id}")
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None


class InventoryServiceClient:
    def __init__(self):
        self.base_url = settings.INVENTORY_SERVICE_URL

    async def check_availability(self, product_id: str, quantity: int) -> dict | None:
        """Check if inventory is available."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/inventory/check",
                    params={"product_id": product_id, "quantity": quantity}
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def reserve(self, product_id: str, quantity: int, order_id: str) -> bool:
        """Reserve inventory for an order."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/inventory/reserve",
                    json={
                        "product_id": product_id,
                        "quantity": quantity,
                        "reference_id": order_id
                    }
                )
                return response.status_code == 200
            except Exception:
                return False

    async def release(self, product_id: str, quantity: int, order_id: str) -> bool:
        """Release reserved inventory."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/inventory/release",
                    json={
                        "product_id": product_id,
                        "quantity": quantity,
                        "reference_id": order_id
                    }
                )
                return response.status_code == 200
            except Exception:
                return False
