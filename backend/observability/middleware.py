"""
Observability Middleware for FastAPI
Auto-logs HTTP requests and responses with trace IDs.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic request/response logging.
    Generates trace IDs and measures endpoint latency.
    """
    
    def __init__(self, app: ASGIApp, trace_logger=None):
        super().__init__(app)
        self.trace_logger = trace_logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log metadata."""
        
        # Generate trace ID
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status = "success"
        except Exception as e:
            status = "error"
            raise
        finally:
            # Calculate latency
            latency = time.time() - start_time
            
            # Log request/response if trace logger available
            if self.trace_logger:
                self.trace_logger.log_trace(
                    trace_id=trace_id,
                    agent_name="HTTPServer",
                    action=f"{request.method} {request.url.path}",
                    input_data={
                        "method": request.method,
                        "path": str(request.url.path),
                        "query_params": dict(request.query_params),
                        "client": request.client.host if request.client else None
                    },
                    output_data={
                        "status_code": response.status_code if 'response' in locals() else 500,
                        "latency_ms": round(latency * 1000, 2)
                    },
                    decision_reason=f"HTTP request processed in {latency*1000:.2f}ms",
                    status=status
                )
        
        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id
        
        return response
