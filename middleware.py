from fastapi import Request
from fastapi.responses import JSONResponse
import time

async def log_requests_middleware(request: Request, call_next):
    """Logging and timing middleware"""
    start_time = time.time()
    
    print(f"→ {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        print(f"← {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        print(f"✗ {request.method} {request.url.path} - Error: {str(e)} - {process_time:.3f}s")
        raise

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"✗ Global error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )