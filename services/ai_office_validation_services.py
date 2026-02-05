"""
AI Office Validation Service Module

Handles AI validation for office SOP compliance events.
"""
from typing import Dict, Any, Optional

from services.base_ai_validation_service import BaseAIValidationService
from services.office_sop_compliance_services import save_office_ai_response_to_audit
from utils.logger import get_logger

logger = get_logger(__name__)


class AIOfficeValidationService(BaseAIValidationService):
    """
    Singleton service for office AI validation API requests.
    
    Extends BaseAIValidationService with:
    - Office AI validation API endpoint
    - Office SOP compliance audit storage
    """
    
    _instance: Optional["AIOfficeValidationService"] = None
    
    def __new__(cls) -> "AIOfficeValidationService":
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
        """Return the office AI validation API URL."""
        return self._settings.ai_office_validation_url
    
    def _save_ai_response(
        self,
        response_data: Dict[str, Any],
        event_folder: str,
        original_meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save AI response to office SOP compliance audit database."""
        try:
            if original_meta:
                self._merge_metadata(response_data, original_meta)
            
            result = save_office_ai_response_to_audit(response_data)
            if not result.get("success"):
                logger.warning(f"Failed to save Office AI response: {result.get('error')}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Error saving Office AI response to audit: {e}")
            return False


# Module-level singleton instance for easy import
ai_office_validation_service = AIOfficeValidationService()
