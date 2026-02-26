"""
AI Validation Service Module

Handles AI validation for standard SOP compliance events.
"""
from typing import Dict, Any, Optional

from services.base_ai_validation_service import BaseAIValidationService
from services.sop_compliance_services import save_ai_response_to_audit
from utils.logger import get_logger

logger = get_logger(__name__)


class AIValidationService(BaseAIValidationService):
    """
    Singleton service for standard AI validation API requests.
    
    Extends BaseAIValidationService with:
    - Standard AI validation API endpoint
    - Standard SOP compliance audit storage
    """
    META_KEYS = frozenset({
        "ts", "cam_id", "cam_name", "zone_names", "site_name", "site_id",
        "latitude", "longitude", "country", "state", "district", "city",
        "company_id", "device_id"
    })

    DATA_DEFAULTS = {
        "triggers": list, "video_count": lambda: 1, "image_count": lambda: 3,
        "detections": list, "triaged_by": str, "triage_notes": str,
        "triage_timestamp": int, "ai_insights": str,
        "capture_triggered": lambda: True, "evidence_path": str,
    }

    def build_event(self, original_meta: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        """Build structured event from raw camera metadata."""
        meta = {k: v for k, v in original_meta.items() if k in self.META_KEYS}
        data = {k: v for k, v in original_meta.items() if k not in self.META_KEYS}
        data.update({k: fn() for k, fn in self.DATA_DEFAULTS.items() if k not in data})
        data.update(overrides)

        return {"type": "event", "meta": meta, "data": data}
    
    _instance: Optional["AIValidationService"] = None
    
    def __new__(cls) -> "AIValidationService":
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
        self._initialized = True
    
    def _get_api_url(self) -> str:
        """Return the standard AI validation API URL."""
        return self._settings.ai_info_validation_url
    
    def _save_ai_response(
        self,
        response_data: Dict[str, Any],
        event_folder: str,
        original_meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save AI response to standard SOP compliance audit database."""
        try:
            if original_meta:
                self._merge_metadata(response_data, original_meta)
            events = [self.build_event(original_meta, evidence_path=event_folder, status="warning")]
            result = save_ai_response_to_audit(response_data, events)
            if not result.get("success"):
                logger.warning(f"Failed to save AI response: {result.get('error')}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Error saving AI response to audit: {e}")
            return False


# Module-level singleton instance for easy import
ai_validation_service = AIValidationService()
