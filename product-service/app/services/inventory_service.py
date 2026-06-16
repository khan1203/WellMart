import httpx
from app.core.config import settings


class InventoryService:
    def __init__(self):
        self.base_url = settings.INVENTORY_SERVICE_URL

    async def create_inventory(self, product_id: str, quantity: int):
        """Create an inventory record for a product in the Inventory Service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/inventory/",
                    json={
                        "product_id": product_id,
                        "available_quantity": quantity,
                        "reorder_threshold": 5
                    }
                )
                if response.status_code == 201:
                    return response.json()
                return None
            except Exception:
                return None

    async def get_inventory(self, product_id: str):
        """Get inventory for a specific product from Inventory Service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/inventory/{product_id}"
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None
