# Placeholder for external service integrations
# Example: Integration with notification services, email services, etc.


class ExternalService:
    """Base class for external service integrations."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url
        self.api_key = api_key


# Example usage:
# class NotificationService(ExternalService):
#     def send_notification(self, user_id: int, message: str):
#         # Implement notification logic
#         pass
