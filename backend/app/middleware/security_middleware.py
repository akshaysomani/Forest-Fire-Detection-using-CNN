import logging
import urllib.parse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.services.security.api_security_service import api_security_service
from app.services.security.threat_detection_engine import threat_detection_engine
from app.core.database import get_db
from app.models.security import SecurityEvent

logger = logging.getLogger("security.middleware")


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Enterprise Security Middleware enforcing:
    - IP address blacklisting
    - Client rate-limiting / DDoS protection
    - SQL injection (SQLi), XSS, and Path Traversal detection
    - Secure HTTP Headers injection (OWASP aligned)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        ip_address = request.client.host if request.client else "127.0.0.1"

        # 1. IP Blacklist Enforcement
        if api_security_service.is_ip_blocked(ip_address):
            logger.warning(f"Blocked request from blacklisted IP: {ip_address}")
            return Response("Access Denied: IP address blacklisted.", status_code=403)

        # 2. Rate Limiting Check
        if not api_security_service.check_rate_limit(ip_address):
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return Response("Rate Limit Exceeded: Too many requests.", status_code=429)

        # 3. Payload and Exploitation Scanning
        path = urllib.parse.unquote(request.url.path)
        query_params = urllib.parse.unquote(str(request.url.query))
        headers = dict(request.headers)

        # Read and cache request body for scanning
        body_str = ""
        # Skip body scanning for upload endpoints to optimize performance & avoid false-positives on binaries
        is_upload = "/upload" in path or "/images" in path or "/datasets" in path

        if not is_upload and request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8", errors="ignore")

            # Override receive channel so endpoint can still consume the body
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request._receive = receive

        is_threat, threat_type = threat_detection_engine.detect_threat(
            method=request.method, path=path, query_params=query_params, headers=headers, body=body_str
        )

        if is_threat:
            logger.warning(f"Threat detected from IP {ip_address}: {threat_type}")
            # Auto block the malicious IP
            api_security_service.block_ip(ip_address)

            # Persist security event to DB if possible (using direct session)
            try:
                # We fetch a database session asynchronously and write the incident
                async for db in get_db():
                    event = SecurityEvent(
                        event_type="THREAT_BLOCKED",
                        severity="CRITICAL",
                        description=f"Malicious request block: {threat_type}",
                        ip_address=ip_address,
                        user_agent=headers.get("user-agent"),
                        details_json={"path": path, "query": query_params, "threat": threat_type},
                    )
                    db.add(event)
                    await db.commit()
                    break
            except Exception as e:
                logger.error(f"Failed to log security event: {e}")

            return Response("Request Rejected: Security threat detected.", status_code=400)

        # 4. Process the request
        response = await call_next(request)

        # 5. Inject OWASP Security Headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
