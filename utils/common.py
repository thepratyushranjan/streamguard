"""
Common utilities for API routes - DRY principle implementation.
"""
from functools import wraps
from typing import Callable, Any, Optional
from fastapi import HTTPException

from utils.logger import get_logger


def create_logger(name: str):
    """Create a logger for the given module name."""
    return get_logger(name)


def success_response(
    message: str = "Operation completed successfully",
    **kwargs
) -> dict:
    """Create a standardized success response."""
    return {"success": True, "message": message, **kwargs}


def handle_route_exceptions(
    error_message: str,
    status_code: int = 500,
    log_error: bool = True
):
    """
    Decorator to handle common route exception patterns.
    
    Args:
        error_message: Base error message for the exception
        status_code: HTTP status code to return on error
        log_error: Whether to log the error with exc_info
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                if log_error:
                    logger.error(f"{error_message}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status_code,
                    detail=f"{error_message}: {str(e)}"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                if log_error:
                    logger.error(f"{error_message}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status_code,
                    detail=f"{error_message}: {str(e)}"
                )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
