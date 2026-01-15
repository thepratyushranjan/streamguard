"""
AI Validation Service Module
"""
import asyncio
from typing import Dict, Any, List, Optional
import httpx

from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AIValidationService:
    """
    Singleton service class for handling AI validation API requests.
    
    Features:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Graceful shutdown support
    """
    
    _instance: Optional["AIValidationService"] = None
    _http_client: Optional[httpx.AsyncClient] = None
    
    # Configuration constants
    MAX_CONCURRENT_VALIDATIONS = 5
    MAX_CONNECTIONS = 100
    MAX_KEEPALIVE_CONNECTIONS = 20
    
    # Timeout configuration (in seconds)
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 120.0  # 2 min for slow APIs
    WRITE_TIMEOUT = 30.0
    POOL_TIMEOUT = 30.0
    
    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    
    def __new__(cls) -> "AIValidationService":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the service (only once due to singleton)."""
        if self._initialized:
            return
        
        self._settings = get_settings()
        self._validation_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_VALIDATIONS)
        self._initialized = True
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with optimized pool settings."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=self.MAX_CONNECTIONS,
                    max_keepalive_connections=self.MAX_KEEPALIVE_CONNECTIONS,
                ),
                timeout=httpx.Timeout(
                    connect=self.CONNECT_TIMEOUT,
                    read=self.READ_TIMEOUT,
                    write=self.WRITE_TIMEOUT,
                    pool=self.POOL_TIMEOUT,
                )
            )
        return self._http_client
    
    async def initialize(self) -> None:
        """Initialize the HTTP client (call on app startup)."""
        _ = self.http_client
        logger.info("AI Validation service HTTP client initialized")
    
    async def shutdown(self) -> None:
        """Close HTTP client gracefully (call on app shutdown)."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("AI Validation service HTTP client closed")
    
    async def _trigger_ai_validation(
        self, 
        validation_payload: Dict[str, Any], 
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> None:
        """
        Execute async AI validation API call with retry logic.
        Uses semaphore to limit concurrent requests.
        
        Args:
            validation_payload: The payload to send to the AI validation API
            max_retries: Maximum number of retry attempts
        """
        event_folder = validation_payload.get('event_folder', 'unknown')
        
        async with self._validation_semaphore:
            for attempt in range(max_retries):
                try:
                    logger.debug(f"AI Validation URL: {self._settings.ai_info_validation_url}")
                    logger.debug(f"AI Validation Payload: {validation_payload}")
                    
                    response = await self.http_client.post(
                        self._settings.ai_info_validation_url,
                        json=validation_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    logger.info(f"AI Validation API success for: {event_folder}")
                    return
                    
                except httpx.TimeoutException:
                    logger.warning(f"AI Validation timeout (attempt {attempt + 1}/{max_retries}): {event_folder}")
                except httpx.HTTPStatusError as e:
                    logger.error(f"AI Validation HTTP error {e.response.status_code}: {event_folder}")
                    logger.error(f"Response body: {e.response.text}")
                    if e.response.status_code < 500:  # Client error - don't retry
                        return
                except Exception as e:
                    logger.error(f"AI Validation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Exponential backoff before retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
            
            logger.error(f"AI Validation failed after {max_retries} retries: {event_folder}")
    
    @staticmethod
    def _build_ai_validation_payload(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the AI validation payload from transformed data item.
        
        Args:
            item: A single item from transformed_data
            
        Returns:
            Formatted AI validation payload
        """
        data = item.get("data", {})
        evidence_path = data.get("evidence_path", "")
        logger.debug(f"file_path: {evidence_path}")
        event_folder = evidence_path.rstrip("/").split("/")[-1] if evidence_path else ""
        
        return {
            "event_folder": event_folder,
            "event_data": {
                "type": item.get("type", ""),
                "processed_at": item.get("processed_at", 0),
                "meta": item.get("meta", {}),
                "data": data
            }
        }
    
    def schedule_ai_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Schedule async AI validation tasks for events with capture_triggered=True.
        Uses asyncio to fire-and-forget without blocking.
        
        Args:
            transformed_data: List of transformed event data items
        """
        for item in transformed_data:
            data = item.get("data", {})
            if data.get("capture_triggered") is True:
                validation_payload = self._build_ai_validation_payload(item)
                event_folder = validation_payload.get("event_folder", "unknown")
                
                # Fire-and-forget: schedule the async task
                asyncio.create_task(self._trigger_ai_validation(validation_payload))
                logger.info(f"AI Validation task queued for: {event_folder}")


# Module-level singleton instance for easy import
ai_validation_service = AIValidationService()

