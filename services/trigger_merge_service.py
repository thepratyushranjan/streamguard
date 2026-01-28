"""
Trigger Merge Service Module

Merges AI-info event_triggers into matching video_analytics_logs records.
Uses a retry queue for reliability in case of transient failures.
"""
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from collections import deque

from clickhouse_connect.driver import Client
from core.connection import get_clickhouse
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MergeTask:
    """Retry queue task for failed trigger merges."""
    event_timestamp: int
    device_id: str
    company_id: str
    triggers: List[str]
    retry_count: int = 0


@dataclass(frozen=True)
class MergeConfig:
    """Trigger merge service configuration."""
    max_queue_size: int = 1000
    retry_interval_seconds: int = 30
    batch_size: int = 10
    max_retries: int = 3


class TriggerMergeService:
    """
    Merges AI-info triggers into video_analytics_logs.
    
    Match criteria: device_id, event_timestamp, company_id
    
    Features:
    - Idempotent merge using arrayDistinct
    - Background retry queue for failures
    - Graceful shutdown support
    """
    
    _instance: Optional["TriggerMergeService"] = None
    CONFIG = MergeConfig()
    
    def __new__(cls) -> "TriggerMergeService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._retry_queue: deque[MergeTask] = deque(maxlen=self.CONFIG.max_queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._initialized = True
        logger.info("TriggerMergeService initialized")
    
    # --- Lifecycle Methods ---
    
    async def start_worker(self) -> None:
        """Start background retry worker."""
        if self._worker_task is None or self._worker_task.done():
            self._shutdown_event.clear()
            self._worker_task = asyncio.create_task(self._retry_worker())
            logger.info("Trigger merge retry worker started")
    
    async def stop_worker(self) -> None:
        """Stop background retry worker gracefully."""
        if self._worker_task and not self._worker_task.done():
            self._shutdown_event.set()
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info(f"Trigger merge worker stopped. Pending: {len(self._retry_queue)}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status for monitoring."""
        return {
            "pending": len(self._retry_queue),
            "max_size": self.CONFIG.max_queue_size,
            "worker_running": self._worker_task is not None and not self._worker_task.done()
        }
    
    # --- Core Merge Logic ---
    
    @staticmethod
    def _escape_string(value: str) -> str:
        """Escape string for ClickHouse SQL."""
        return value.replace("'", "\\'").replace("\\", "\\\\")
    
    @staticmethod
    def _build_triggers_array(triggers: List[str]) -> str:
        """Build ClickHouse array literal from triggers list."""
        escaped = [f"'{TriggerMergeService._escape_string(t)}'" for t in triggers]
        return f"[{', '.join(escaped)}]"
    
    def merge_triggers(
        self,
        event_timestamp: int,
        device_id: str,
        company_id: str,
        triggers: List[str],
        client: Optional[Client] = None
    ) -> Dict[str, Any]:
        """
        Merge AI-info triggers into matching video_analytics_logs record.
        
        Match criteria: event_timestamp, device_id, company_id
        Uses arrayDistinct(arrayConcat(...)) for idempotent merge.
        """
        if not triggers:
            return {"merged": False, "reason": "No triggers to merge"}
        
        try:
            db_client = get_clickhouse(company_id)
            
            # Escape values for SQL
            device_escaped = self._escape_string(device_id)
            company_escaped = self._escape_string(company_id)
            triggers_array = self._build_triggers_array(triggers)
            
            logger.info(
                f"[MERGE] Attempting: ts={event_timestamp}, device={device_id}, "
                f"company={company_id}, triggers={triggers}"
            )
            
            # Check if matching record exists
            check_query = f"""
                SELECT count(*) FROM video_analytics_logs 
                WHERE event_timestamp = {event_timestamp}
                  AND device_id = '{device_escaped}'
                  AND company_id = '{company_escaped}'
            """
            
            result = db_client.query(check_query)
            count = result.result_rows[0][0] if result.result_rows else 0
            
            if count == 0:
                logger.warning(
                    f"[MERGE] No matching record: ts={event_timestamp}, "
                    f"device={device_id}, company={company_id}"
                )
                return {"merged": False, "reason": "No matching event record found"}
            
            logger.debug(f"[MERGE] Found {count} matching record(s)")
            
            # Execute merge mutation
            update_query = f"""
                ALTER TABLE video_analytics_logs
                UPDATE event_triggers = arrayDistinct(arrayConcat(event_triggers, {triggers_array}))
                WHERE event_timestamp = {event_timestamp}
                  AND device_id = '{device_escaped}'
                  AND company_id = '{company_escaped}'
            """
            
            db_client.command(update_query)
            
            logger.info(
                f"[MERGE SUCCESS] {len(triggers)} triggers merged: "
                f"ts={event_timestamp}, device={device_id}"
            )
            
            return {"merged": True, "triggers_count": len(triggers)}
            
        except Exception as e:
            logger.error(f"[MERGE ERROR] {e}", exc_info=True)
            self._add_to_retry_queue(MergeTask(
                event_timestamp=event_timestamp,
                device_id=device_id,
                company_id=company_id,
                triggers=triggers
            ))
            return {"merged": False, "error": str(e), "queued_for_retry": True}
    
    # --- Retry Queue ---
    
    def _add_to_retry_queue(self, task: MergeTask) -> None:
        """Add failed task to retry queue."""
        if task.retry_count < self.CONFIG.max_retries:
            task.retry_count += 1
            self._retry_queue.append(task)
            logger.info(f"Queued for retry ({task.retry_count}/{self.CONFIG.max_retries}): ts={task.event_timestamp}")
        else:
            logger.error(f"Max retries exceeded, dropping: ts={task.event_timestamp}, triggers={task.triggers}")
    
    async def _retry_worker(self) -> None:
        """Background worker processing retry queue."""
        logger.info("Retry worker started")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for interval or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.CONFIG.retry_interval_seconds
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Process queue
                
                if not self._retry_queue:
                    continue
                
                # Process batch
                batch_size = min(self.CONFIG.batch_size, len(self._retry_queue))
                logger.debug(f"Processing {batch_size} retry tasks")
                
                for _ in range(batch_size):
                    if not self._retry_queue or self._shutdown_event.is_set():
                        break
                    
                    task = self._retry_queue.popleft()
                    self.merge_triggers(
                        event_timestamp=task.event_timestamp,
                        device_id=task.device_id,
                        company_id=task.company_id,
                        triggers=task.triggers
                    )
                    await asyncio.sleep(0.1)  # Rate limiting
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry worker error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info("Retry worker stopped")


# Singleton instance
trigger_merge_service = TriggerMergeService()
