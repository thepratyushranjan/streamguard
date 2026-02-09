import asyncio
import random
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Awaitable
from utils.logger import get_logger
from core.config import get_settings
import httpx


# Configuration Dataclasses
@dataclass(frozen=True)
class ConnectionConfig:
    """HTTP connection pool configuration."""
    max_connections: int = 100
    max_keepalive: int = 20

    def to_httpx_limits(self) -> httpx.Limits:
        """Convert to httpx.Limits object."""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive,
        )


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
    """
    Production-level retry configuration.
    
    Exponential backoff with jitter prevents thundering herd problem.
    With jitter: actual wait = base_wait * random(jitter_min, jitter_max)
    """
    max_retries: int
    base_backoff: int
    max_backoff: int
    jitter_min: float
    jitter_max: float


# Default configurations (can be overridden)
DEFAULT_CONNECTION_CONFIG = ConnectionConfig()
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig()


def get_retry_config() -> RetryConfig:
    """Get retry config from environment settings."""
    settings = get_settings()
    return RetryConfig(
        max_retries=settings.retry_max_retries,
        base_backoff=settings.retry_base_backoff,
        max_backoff=settings.retry_max_backoff,
        jitter_min=settings.retry_jitter_min,
        jitter_max=settings.retry_jitter_max,
    )


# For backwards compatibility
DEFAULT_RETRY_CONFIG = get_retry_config()

# Retry Utility Functions
async def execute_with_retry(
    operation: Callable[[], Awaitable[Any]],
    context: str,
    logger,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG,
    max_retries: Optional[int] = None
) -> Optional[Any]:
    """
    Execute an async operation with retry logic and exponential backoff.
    
    This is a standalone function that can be used by any service.
    
    Args:
        operation: Async callable to execute
        context: Context string for logging (e.g., event_folder)
        logger: Logger instance for logging
        retry_config: Retry configuration
        max_retries: Override default max retries
    
    Returns:
        Operation result or None if all retries failed
    """
    retries = max_retries or retry_config.max_retries
    
    for attempt in range(retries):
        try:
            if attempt > 0:
                logger.info(f"Retry {attempt} for: {context}")
            return await operation()
        except httpx.TimeoutException:
            logger.warning(f"Timeout (attempt {attempt + 1}/{retries}): {context}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {context}")
            logger.error(f"Response body: {e.response.text}")
            if e.response.status_code < 500:
                return None
        except Exception as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            wait_time = calculate_backoff_with_jitter(attempt, retry_config)
            logger.info(f"Waiting {wait_time:.1f}s before retry {attempt + 1}: {context}")
            await asyncio.sleep(wait_time)
    
    logger.error(f"All {retries} retries exhausted: {context}")
    return None


def calculate_backoff_with_jitter(
    attempt: int,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG
) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        retry_config: Retry configuration
    
    Returns:
        Wait time in seconds with jitter applied
    """
    # Calculate base exponential wait: 2^1=2s, 2^2=4s, 2^3=8s, 2^4=16s
    base_wait = retry_config.base_backoff ** (attempt + 1)
    # Cap at maximum backoff
    capped_wait = min(base_wait, retry_config.max_backoff)
    # Apply jitter to prevent thundering herd
    jitter = random.uniform(retry_config.jitter_min, retry_config.jitter_max)
    return capped_wait * jitter

# HTTP Client Management
def create_http_client(
    connection_config: ConnectionConfig = DEFAULT_CONNECTION_CONFIG,
    timeout_config: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG
) -> httpx.AsyncClient:
    """
    Create an HTTP client with optimized pool settings.
    
    Args:
        connection_config: Connection pool configuration
        timeout_config: Timeout configuration
    
    Returns:
        Configured httpx.AsyncClient
    """
    return httpx.AsyncClient(
        limits=connection_config.to_httpx_limits(),
        timeout=timeout_config.to_httpx_timeout()
    )

# Payload Builder Utility
def build_validation_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the validation payload from transformed data item.
    
    This is the standard format used by all validation services.
    
    Args:
        item: A single item from transformed_data
        
    Returns:
        Formatted validation payload
    """
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


# Base HTTP Service Class
class BaseHTTPService(ABC):
    """
    Abstract base class for HTTP-based services.
    
    Provides:
    - HTTP client lifecycle management
    - Concurrency control via semaphore
    - Queue-based batch processing with delayed execution
    - Graceful shutdown support
    
    Subclasses must implement:
    - _get_api_url(): Return the API endpoint URL
    - _process_response(): Process API response
    - _build_payload(): Build request payload from item
    """
    
    _http_client: Optional[httpx.AsyncClient] = None
    
    # Configuration (use dataclasses)
    MAX_CONCURRENT_REQUESTS = 5
    CONNECTION_CFG = DEFAULT_CONNECTION_CONFIG
    TIMEOUT_CFG = DEFAULT_TIMEOUT_CONFIG
    RETRY_CFG = DEFAULT_RETRY_CONFIG
    
    # Batch processing delay (in seconds)
    BATCH_DELAY_SECONDS = 30
    
    def __init__(self) -> None:
        """Initialize the service instance."""
        self._logger = get_logger(self.__class__.__name__)
        self._request_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        
        # Queue-based batching
        self._event_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
        self._batch_timer: Optional[threading.Timer] = None
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with optimized pool settings."""
        if self._http_client is None:
            self._http_client = create_http_client(
                self.CONNECTION_CFG,
                self.TIMEOUT_CFG
            )
        return self._http_client
    
    async def initialize(self) -> None:
        """Initialize the HTTP client (call on app startup)."""
        _ = self.http_client
        self._logger.info(f"{self.__class__.__name__} HTTP client initialized")
    
    async def shutdown(self) -> None:
        """Close HTTP client gracefully (call on app shutdown)."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            self._logger.info(f"{self.__class__.__name__} HTTP client closed")
    
    @abstractmethod
    def _get_api_url(self) -> str:
        """Return the API endpoint URL. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _build_payload(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Build request payload from item. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _process_response(
        self,
        response: httpx.Response,
        payload: Dict[str, Any]
    ) -> Optional[Any]:
        """Process API response. Must be implemented by subclasses."""
        pass
    
    async def _execute_request(
        self,
        payload: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Optional[Any]:
        """
        Execute API request with retry logic.
        Uses semaphore to limit concurrent requests.
        """
        context = payload.get('event_folder', 'unknown')
        
        async def _make_request() -> httpx.Response:
            response = await self.http_client.post(
                self._get_api_url(),
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response
        
        async with self._request_semaphore:
            response = await execute_with_retry(
                _make_request,
                context,
                self._logger,
                self.RETRY_CFG,
                max_retries
            )
            if response:
                return await self._process_response(response, payload)
        return None
    
    def queue_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Queue events for batch processing after a delay.
        Events are collected and processed together after BATCH_DELAY_SECONDS.
        """
        with self._queue_lock:
            self._event_queue.extend(transformed_data)
            queue_size = len(self._event_queue)
            
            if self._batch_timer is None or not self._batch_timer.is_alive():
                self._batch_timer = threading.Timer(
                    self.BATCH_DELAY_SECONDS,
                    self._process_queued_events
                )
                self._batch_timer.daemon = True
                self._batch_timer.start()
                self._logger.info(
                    f"Started batch timer for {self.BATCH_DELAY_SECONDS}s "
                    f"with {queue_size} events"
                )
            else:
                self._logger.debug(
                    f"Added {len(transformed_data)} events to queue "
                    f"(total: {queue_size})"
                )
    
    def _process_queued_events(self) -> None:
        """
        Process all queued events. Called by the batch timer.
        This runs in a separate thread, so we need to create a new event loop.
        """
        with self._queue_lock:
            if not self._event_queue:
                self._logger.debug("No events in queue to process")
                return
            
            events_to_process = self._event_queue.copy()
            self._event_queue.clear()
            self._batch_timer = None
        
        self._logger.info(f"Processing batch of {len(events_to_process)} events")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_batch(events_to_process))
            finally:
                loop.close()
        except Exception as e:
            self._logger.error(f"Error processing batch: {e}")
    
    async def _run_batch(self, events: List[Dict[str, Any]]) -> None:
        """Run batch requests asynchronously."""
        tasks = []
        for item in events:
            payload = self._build_payload(item)
            tasks.append(self._execute_request(payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def schedule_immediate_tasks(self, transformed_data: List[Dict[str, Any]]) -> None:
        """
        Schedule async tasks for immediate execution (fire-and-forget).
        """
        for item in transformed_data:
            payload = self._build_payload(item)
            event_folder = payload.get("event_folder", "unknown")
            asyncio.create_task(self._execute_request(payload))
            self._logger.info(f"Task queued for: {event_folder}")
