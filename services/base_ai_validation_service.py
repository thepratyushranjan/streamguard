"""
Base AI Validation Service Module

Shared base class for all AI validation services.
Provides HTTP client management, retry logic, and queue-based batch processing.
"""
import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Awaitable
import httpx

from core.config import get_settings
from utils.logger import get_logger


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


class BaseAIValidationService(ABC):
    """
    Abstract base service for AI validation API requests.
    
    Features:
    - Connection pooling with configurable limits
    - Concurrency control via semaphore
    - Automatic retry with exponential backoff
    - Queue-based batching with delayed processing
    - Graceful shutdown support
    
    Subclasses must implement:
    - _get_api_url(): Return the API endpoint URL
    - _save_ai_response(): Save response to appropriate audit table
    """
    
    _http_client: Optional[httpx.AsyncClient] = None
    
    # Configuration (use dataclasses for grouping)
    MAX_CONCURRENT_VALIDATIONS = 5
    CONNECTION_CFG = ConnectionConfig()
    TIMEOUT_CFG = TimeoutConfig()
    RETRY_CFG = RetryConfig()
    
    # Batch processing delay (in seconds)
    BATCH_DELAY_SECONDS = 30
    
    # Fields to copy from original event metadata
    _META_FIELDS = (
        'company_id', 'device_id', 'cam_id', 'cam_name', 'site_name',
        'site_id', 'latitude', 'longitude', 'country', 'state', 'district', 'city'
    )
    
    def __init__(self) -> None:
        """Initialize the service instance."""
        self._settings = get_settings()
        self._logger = get_logger(self.__class__.__name__)
        self._validation_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_VALIDATIONS)
        
        # Queue-based batching
        self._event_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        self._batch_timer: Optional[threading.Timer] = None
    
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
        self._logger.info("AI Validation service HTTP client initialized")
    
    async def shutdown(self) -> None:
        """Close HTTP client gracefully (call on app shutdown)."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            self._logger.info("AI Validation service HTTP client closed")
    
    @abstractmethod
    def _get_api_url(self) -> str:
        """Return the AI validation API URL. Must be implemented by subclasses."""
        pass
    
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
        # Fill missing fields from original meta
        for key in self._META_FIELDS:
            if not meta.get(key) and original_meta.get(key):
                meta[key] = original_meta[key]
        # Map 'ts' to 'event_timestamp' if missing
        if not meta.get('event_timestamp') and original_meta.get('ts'):
            meta['event_timestamp'] = int(original_meta['ts'])
    
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
                self._logger.warning(f"Timeout (attempt {attempt + 1}/{retries}): {context}")
            except httpx.HTTPStatusError as e:
                self._logger.error(f"HTTP error {e.response.status_code}: {context}")
                self._logger.error(f"Response body: {e.response.text}")
                if e.response.status_code < 500:  # Client error - don't retry
                    return None
            except Exception as e:
                self._logger.error(f"Failed (attempt {attempt + 1}/{retries}): {e}")
            
            # Exponential backoff before retry
            if attempt < retries - 1:
                wait_time = self.RETRY_CFG.base_backoff ** attempt
                await asyncio.sleep(wait_time)
        
        self._logger.error(f"Failed after {retries} retries: {context}")
        return None
    
    async def _trigger_ai_validation(
        self,
        validation_payload: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute async AI validation API call with retry logic.
        Uses semaphore to limit concurrent requests.
        """
        event_folder = validation_payload.get('event_folder', 'unknown')
        
        async def _make_request() -> httpx.Response:
            response = await self.http_client.post(
                self._get_api_url(),
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
                self._logger.info(f"AI Validation complete ({status}): {event_folder}")
                return response_data
        return None
    
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
    
    def queue_ai_validation_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Queue events for batch AI validation after a delay.
        Events are collected and processed together after BATCH_DELAY_SECONDS.
        
        This is more efficient than creating individual timers for each request,
        as it uses a single timer for all queued events.
        
        Args:
            transformed_data: List of transformed event data items
        """
        with self._queue_lock:
            # Add all events to the queue
            self._event_queue.extend(transformed_data)
            queue_size = len(self._event_queue)
            
            # Start timer if not already running
            if self._batch_timer is None or not self._batch_timer.is_alive():
                self._batch_timer = threading.Timer(
                    self.BATCH_DELAY_SECONDS,
                    self._process_queued_events
                )
                self._batch_timer.daemon = True
                self._batch_timer.start()
                self._logger.info(f"Started AI validation batch timer for {self.BATCH_DELAY_SECONDS}s with {queue_size} events")
            else:
                self._logger.debug(f"Added {len(transformed_data)} AI events to queue (total: {queue_size})")
    
    def _process_queued_events(self) -> None:
        """
        Process all queued events. Called by the batch timer.
        This runs in a separate thread, so we need to create a new event loop.
        """
        with self._queue_lock:
            if not self._event_queue:
                self._logger.debug("No AI events in queue to process")
                return
            
            # Take all events from queue
            events_to_process = self._event_queue.copy()
            self._event_queue.clear()
            self._batch_timer = None
        
        self._logger.info(f"Processing batch of {len(events_to_process)} AI validation events")
        
        # Create a new event loop for this thread and run validations
        # This avoids "Event loop is closed" errors since timer runs in a separate thread
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_batch_validations(events_to_process))
            finally:
                loop.close()
        except Exception as e:
            self._logger.error(f"Error processing AI validation batch: {e}")
    
    async def _run_batch_validations(self, events: List[Dict[str, Any]]) -> None:
        """Run batch AI validations asynchronously."""
        tasks = []
        for item in events:
            payload = self._build_ai_validation_payload(item)
            tasks.append(self._trigger_ai_validation(payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
