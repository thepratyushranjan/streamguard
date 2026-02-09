from abc import abstractmethod
from typing import Dict, Any, Optional
import httpx

from core.config import get_settings
from services.http_service_base import (
    BaseHTTPService,
    build_validation_payload,
)


class BaseAIValidationService(BaseHTTPService):
    """
    Abstract base service for AI validation API requests.
    
    Inherits from BaseHTTPService:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Queue-based batching with delayed processing
    - Graceful shutdown support
    
    Subclasses must implement:
    - _get_api_url(): Return the API endpoint URL
    - _save_ai_response(): Save response to appropriate audit table
    """
    
    # Fields to copy from original event metadata
    _META_FIELDS = (
        'company_id', 'device_id', 'cam_id', 'cam_name', 'site_name',
        'site_id', 'latitude', 'longitude', 'country', 'state', 'district', 'city'
    )
    
    def __init__(self) -> None:
        """Initialize the service instance."""
        super().__init__()
        self._settings = get_settings()
    
    def _build_payload(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Build validation payload from item."""
        return build_validation_payload(item)
    
    @abstractmethod
    def _save_ai_response(
        self,
        response_data: Dict[str, Any],
        event_folder: str,
        original_meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save AI response to audit database. Must be implemented by subclasses."""
        pass
    
    def _merge_metadata(
        self,
        response_data: Dict[str, Any],
        original_meta: Dict[str, Any]
    ) -> None:
        """Merge original event metadata into response data."""
        meta = response_data.setdefault('metadata', {})
        for key in self._META_FIELDS:
            if not meta.get(key) and original_meta.get(key):
                meta[key] = original_meta[key]
        if not meta.get('event_timestamp') and original_meta.get('ts'):
            meta['event_timestamp'] = int(original_meta['ts'])
    
    async def _process_response(
        self,
        response: httpx.Response,
        payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process AI validation API response."""
        event_folder = payload.get('event_folder', 'unknown')
        response_json = response.json()
        response_data = response_json.get('validation_result', response_json)
        original_meta = payload.get('event_data', {}).get('meta', {})
        
        saved = self._save_ai_response(response_data, event_folder, original_meta)
        status = "saved to audit" if saved else "API OK, audit save failed"
        self._logger.info(f"AI Validation complete ({status}): {event_folder}")
        return response_data
    
    def queue_ai_validation_tasks(self, transformed_data) -> None:
        """Queue events for batch AI validation (delegates to base class)."""
        self.queue_tasks(transformed_data)
