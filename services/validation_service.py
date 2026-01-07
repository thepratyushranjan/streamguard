"""
Validation Service Module
"""
import asyncio
from typing import Dict, Any, List, Optional
import httpx

from config import get_settings


class ValidationService:
    """
    Singleton service class for handling validation API requests.
    
    Features:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Graceful shutdown support
    """
    
    _instance: Optional["ValidationService"] = None
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
    
    def __new__(cls) -> "ValidationService":
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
        print("✓ Validation service HTTP client initialized")
    
    async def shutdown(self) -> None:
        """Close HTTP client gracefully (call on app shutdown)."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            print("✓ Validation service HTTP client closed")
    
    async def _trigger_validation(
        self, 
        validation_payload: Dict[str, Any], 
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> None:
        """
        Execute async validation API call with retry logic.
        Uses semaphore to limit concurrent requests.
        
        Args:
            validation_payload: The payload to send to the validation API
            max_retries: Maximum number of retry attempts
        """
        event_folder = validation_payload.get('event_folder', 'unknown')
        
        async with self._validation_semaphore:
            for attempt in range(max_retries):
                try:
                    # Debug logging
                    print(f"→ Validation URL: {self._settings.validation_url}")
                    print(f"→ Validation Payload: {validation_payload}")
                    
                    response = await self.http_client.post(
                        self._settings.validation_url,
                        json=validation_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    print(f"✓ Validation API success for: {event_folder}")
                    return
                    
                except httpx.TimeoutException:
                    print(f"⚠ Validation timeout (attempt {attempt + 1}/{max_retries}): {event_folder}")
                except httpx.HTTPStatusError as e:
                    print(f"✗ Validation HTTP error {e.response.status_code}: {event_folder}")
                    print(f"✗ Response body: {e.response.text}")  # Show error details
                    if e.response.status_code < 500:  # Client error - don't retry
                        return
                except Exception as e:
                    print(f"✗ Validation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Exponential backoff before retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
            
            print(f"✗ Validation failed after {max_retries} retries: {event_folder}")
    
    @staticmethod
    def _build_validation_payload(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the validation payload from transformed data item.
        
        Args:
            item: A single item from transformed_data
            
        Returns:
            Formatted validation payload
        """
        data = item.get("data", {})
        evidence_path = data.get("evidence_path", "")
        print(f"""file_path:{evidence_path}""")
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
    
    def schedule_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Schedule async validation tasks for events with capture_triggered=True.
        Uses asyncio to fire-and-forget without blocking.
        
        Args:
            transformed_data: List of transformed event data items
        """
        for item in transformed_data:
            data = item.get("data", {})
            if data.get("capture_triggered") is True:
                validation_payload = self._build_validation_payload(item)
                event_folder = validation_payload.get("event_folder", "unknown")
                
                # Fire-and-forget: schedule the async task
                asyncio.create_task(self._trigger_validation(validation_payload))
                print(f"→ Validation task queued for: {event_folder}")


# Module-level singleton instance for easy import
validation_service = ValidationService()
