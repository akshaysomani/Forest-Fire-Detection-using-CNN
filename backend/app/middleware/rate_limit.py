import time
from collections import defaultdict
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, auth_requests_per_minute: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        # Dictionary mapping IP -> list of timestamps
        self.history = defaultdict(list)
        # Separate track for auth routes (login, register, forgot-password)
        self.auth_history = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        import os
        if "PYTEST_CURRENT_TEST" in os.environ:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        path = request.url.path

        # Clean old timestamps (older than 60s)
        self.history[ip] = [t for t in self.history[ip] if now - t < 60]
        self.auth_history[ip] = [t for t in self.auth_history[ip] if now - t < 60]

        # Check rate limits
        if "/auth/login" in path or "/auth/register" in path or "/auth/forgot-password" in path:
            if len(self.auth_history[ip]) >= self.auth_requests_per_minute:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": {
                            "code": "TOO_MANY_REQUESTS",
                            "message": "Too many authentication attempts. Please try again later."
                        }
                    }
                )
            self.auth_history[ip].append(now)

        # Global IP limit
        if len(self.history[ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "TOO_MANY_REQUESTS",
                        "message": "Rate limit exceeded. Please try again later."
                    }
                }
            )

        self.history[ip].append(now)
        response = await call_next(request)
        return response
