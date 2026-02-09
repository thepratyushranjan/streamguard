from typing import Dict, Any, List, Optional
import httpx

from core.config import get_settings
from utils.logger import get_logger
from services.http_service_base import (
    BaseHTTPService,
    build_validation_payload,
)

logger = get_logger(__name__)


class ValidationService(BaseHTTPService):
    """
    Singleton service class for handling validation API requests.
    
    Inherits from BaseHTTPService:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Queue-based batching with delayed processing
    - Graceful shutdown support
    """
    
    _instance: Optional["ValidationService"] = None
    
    def __new__(cls) -> "ValidationService":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the service (only once due to singleton)."""
        if getattr(self, '_initialized', False):
            return
        super().__init__()
        self._settings = get_settings()
        self._initialized = True
    
    def _get_api_url(self) -> str:
        """Return the validation API URL."""
        return self._settings.validation_url
    
    def _build_payload(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Build validation payload from item."""
        return build_validation_payload(item)
    
    async def _process_response(
        self,
        response: httpx.Response,
        payload: Dict[str, Any]
    ) -> None:
        """Process validation API response."""
        event_folder = payload.get('event_folder', 'unknown')
        logger.debug(f"Validation URL: {self._settings.validation_url}")
        logger.debug(f"Validation Payload: {payload}")
        logger.info(f"Validation API success for: {event_folder}")
    
    def schedule_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """Schedule async validation tasks (delegates to base class)."""
        self.schedule_immediate_tasks(transformed_data)
    
    def queue_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """Queue events for batch validation (delegates to base class)."""
        self.queue_tasks(transformed_data)


# Module-level singleton instance for easy import
validation_service = ValidationService()
