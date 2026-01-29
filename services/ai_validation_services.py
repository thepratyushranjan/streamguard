"""
AI Validation Service Module
"""
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Awaitable
import httpx

from core.config import get_settings
from utils.logger import get_logger
from services.sop_compliance_services import save_ai_response_to_audit

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
    # Fields to copy from original event metadata
    _META_FIELDS = ('company_id', 'device_id', 'cam_id', 'cam_name', 'site_name',
                    'site_id', 'latitude', 'longitude', 'country', 'state', 'district', 'city')
    
    def _save_ai_response(self, response_data: Dict[str, Any], event_folder: str, original_meta: Dict[str, Any] = None) -> bool:
        """Save AI response to audit database, merging original metadata if needed."""
        try:
            if original_meta:
                meta = response_data.setdefault('metadata', {})
                # Fill missing fields from original meta
                for key in self._META_FIELDS:
                    if not meta.get(key) and original_meta.get(key):
                        meta[key] = original_meta[key]
                # Map 'ts' to 'event_timestamp' if missing
                if not meta.get('event_timestamp') and original_meta.get('ts'):
                    meta['event_timestamp'] = int(original_meta['ts'])
            
            result = save_ai_response_to_audit(response_data)
            if not result.get("success"):
                logger.warning(f"Failed to save AI response: {result.get('error')}")
            return result.get("success", False)
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
                # Merge original event metadata into AI response (in case AI doesn't return it)
                response_json = response.json()
                # Extract validation_result from nested response structure
                response_data = response_json.get('validation_result', response_json)
                original_meta = validation_payload.get('event_data', {}).get('meta', {})
                saved = self._save_ai_response(response_data, event_folder, original_meta)
                status = "saved to audit" if saved else "API OK, audit save failed"
                logger.info(f"AI Validation complete ({status}): {event_folder}")
    
    @staticmethod
    def _build_ai_validation_payload(item: Dict[str, Any]) -> Dict[str, Any]:
        """Build the AI validation payload from transformed data item."""
        data = item.get("data", {})
        evidence_path = data.get("evidence_path", "")
        return {
            "event_folder": evidence_path,
            "event_data": {
                "type": item.get("type", ""),
                "processed_at": item.get("processed_at", 0),
                "meta": item.get("meta", {}),
                "data": data
            }
        }
    
    def schedule_ai_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Schedule async AI validation tasks for all events.
        Uses asyncio to fire-and-forget without blocking.
        """
        for item in transformed_data:
            payload = self._build_ai_validation_payload(item)
            event_folder = payload.get("event_folder", "unknown")
            asyncio.create_task(self._trigger_ai_validation(payload))
            logger.info(f"AI Validation task queued for: {event_folder}")


# Module-level singleton instance for easy import
ai_validation_service = AIValidationService()

