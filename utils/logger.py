"""
Centralized Logger Module for StreamGuard

Production-ready logging with:
- Configurable log levels via LOG_LEVEL env variable
- JSON structured logging for production (LOG_FORMAT=json)
- Pretty console output for development
- Singleton pattern for consistent logging across all modules
"""

import logging
import os
import sys
import json
from datetime import datetime
from typing import Optional
from functools import lru_cache


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    # Status emojis for visual clarity
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠',
        'ERROR': '✗',
        'CRITICAL': '💥'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color and emoji
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        emoji = self.EMOJIS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build formatted message
        formatted = (
            f"{color}{timestamp} | {emoji} {record.levelname:<8}{reset} | "
            f"{record.name}:{record.funcName}:{record.lineno} - {record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data)


class StreamGuardLogger:
    """
    Singleton logger class for StreamGuard application.
    
    Environment Variables:
        LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
        LOG_FORMAT: json, console (default: console)
    """
    
    _instance: Optional["StreamGuardLogger"] = None
    _loggers: dict = {}
    
    def __new__(cls) -> "StreamGuardLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._log_level = self._get_log_level()
        self._log_format = os.getenv("LOG_FORMAT", "console").lower()
        self._initialized = True
        
        # Configure root logger
        self._configure_root_logger()
    
    @staticmethod
    def _get_log_level() -> int:
        """Get log level from environment variable."""
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        return getattr(logging, level_name, logging.INFO)
    
    def _configure_root_logger(self) -> None:
        """Configure the root logger with appropriate handler and formatter."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self._log_level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._log_level)
        
        # Set formatter based on environment
        if self._log_format == "json":
            formatter = JSONFormatter()
        else:
            formatter = ColoredFormatter()
        
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Logger name (typically __name__ of the calling module)
            
        Returns:
            Configured logger instance
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(self._log_level)
            self._loggers[name] = logger
        
        return self._loggers[name]


# Module-level singleton instance
_logger_instance = StreamGuardLogger()


@lru_cache(maxsize=32)
def get_logger(name: str = "streamguard") -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        
        logger.info("Application started")
        logger.error("Something went wrong", exc_info=True)
    
    Args:
        name: Module name (use __name__ for automatic module detection)
        
    Returns:
        Configured logger instance
    """
    return _logger_instance.get_logger(name)


# Default logger for quick imports
logger = get_logger("streamguard")
