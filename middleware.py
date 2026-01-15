from fastapi import Request
from fastapi.responses import JSONResponse
import time
from utils.logger import get_logger

logger = get_logger(__name__)


async def log_requests_middleware(request: Request, call_next):
    """Logging and timing middleware"""
    start_time = time.time()
    
    logger.debug(f"→ {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"← {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} - Error: {str(e)} - {process_time:.3f}s")
        raise


async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )