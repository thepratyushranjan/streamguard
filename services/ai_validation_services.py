"""
AI Validation Service Module
"""
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Awaitable
import httpx

from core.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


# Configuration dataclasses (DRY: group related constants)
@dataclass(frozen=True)
class ConnectionConfig:
    """HTTP connection pool configuration."""
    max_connections: int = 100
    max_keepalive: int = 20


@dataclass(frozen=True)
class TimeoutConfig:
    """HTTP timeout configuration (seconds)."""
    connect: float = 10.0
    read: float = 120.0  # 2 min for slow APIs
    write: float = 30.0
    pool: float = 30.0

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout object."""
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool
        )


@dataclass(frozen=True)  
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    base_backoff: int = 2  # Exponential base (2^attempt seconds)


class AIValidationService:
    """
    Singleton service for AI validation API requests.
    
    Features:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Graceful shutdown support
    """
    
    _instance: Optional["AIValidationService"] = None
    _http_client: Optional[httpx.AsyncClient] = None
    
    # Configuration (use dataclasses for grouping)
    MAX_CONCURRENT_VALIDATIONS = 5
    CONNECTION_CFG = ConnectionConfig()
    TIMEOUT_CFG = TimeoutConfig()
    RETRY_CFG = RetryConfig()
    
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
                    max_connections=self.CONNECTION_CFG.max_connections,
                    max_keepalive_connections=self.CONNECTION_CFG.max_keepalive,
                ),
                timeout=self.TIMEOUT_CFG.to_httpx_timeout()
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
    
    async def _execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        context: str,
        max_retries: Optional[int] = None
    ) -> Optional[Any]:
        """
        Execute an async operation with retry logic and exponential backoff.
        
        Args:
            operation: Async callable to execute
            context: Context string for logging (e.g., event_folder)
            max_retries: Override default max retries
        
        Returns:
            Operation result or None if all retries failed
        """
        retries = max_retries or self.RETRY_CFG.max_retries
        
        for attempt in range(retries):
            try:
                return await operation()
            except httpx.TimeoutException:
                logger.warning(f"Timeout (attempt {attempt + 1}/{retries}): {context}")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {context}")
                logger.error(f"Response body: {e.response.text}")
                if e.response.status_code < 500:  # Client error - don't retry
                    return None
            except Exception as e:
                logger.error(f"Failed (attempt {attempt + 1}/{retries}): {e}")
            
            # Exponential backoff before retry
            if attempt < retries - 1:
                wait_time = self.RETRY_CFG.base_backoff ** attempt
                await asyncio.sleep(wait_time)
        
        logger.error(f"Failed after {retries} retries: {context}")
        return None
    
    def _save_ai_response(self, response_data: Dict[str, Any], event_folder: str) -> bool:
        """Save AI response to audit database. Returns True if successful."""
        try:
            from services.sop_compliance_services import save_ai_response_to_audit
            result = save_ai_response_to_audit(response_data)
            if result.get("success"):
                return True
            logger.warning(f"Failed to save AI response: {result.get('error')}")
            return False
        except Exception as e:
            logger.error(f"Error saving AI response to audit: {e}")
            return False
    
    async def _trigger_ai_validation(
        self, 
        validation_payload: Dict[str, Any], 
        max_retries: Optional[int] = None
    ) -> None:
        """
        Execute async AI validation API call with retry logic.
        Uses semaphore to limit concurrent requests.
        """
        event_folder = validation_payload.get('event_folder', 'unknown')
        
        async def _make_request() -> httpx.Response:
            logger.debug(f"AI Validation URL: {self._settings.ai_info_validation_url}")
            logger.debug(f"AI Validation Payload: {validation_payload}")
            response = await self.http_client.post(
                self._settings.ai_info_validation_url,
                json=validation_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response
        
        async with self._validation_semaphore:
            response = await self._execute_with_retry(_make_request, event_folder, max_retries)
            if response:
                saved = self._save_ai_response(response.json(), event_folder)
                status = "saved to audit" if saved else "API OK, audit save failed"
                logger.info(f"AI Validation complete ({status}): {event_folder}")
    
    @staticmethod
    def _extract_event_folder(evidence_path: str) -> str:
        """Extract event folder name from evidence path."""
        return evidence_path.rstrip("/").split("/")[-1] if evidence_path else ""
    
    @staticmethod
    def _build_ai_validation_payload(item: Dict[str, Any]) -> Dict[str, Any]:
        """Build the AI validation payload from transformed data item."""
        data = item.get("data", {})
        evidence_path = data.get("evidence_path", "")
        logger.debug(f"file_path: {evidence_path}")
        
        return {
            "event_folder": AIValidationService._extract_event_folder(evidence_path),
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
        """
        for item in transformed_data:
            if item.get("data", {}).get("capture_triggered") is True:
                payload = self._build_ai_validation_payload(item)
                event_folder = payload.get("event_folder", "unknown")
                asyncio.create_task(self._trigger_ai_validation(payload))
                logger.info(f"AI Validation task queued for: {event_folder}")


# Module-level singleton instance for easy import
ai_validation_service = AIValidationService()

