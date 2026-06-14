import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("security.audit")


class SecurityAuditLogger:
    @staticmethod
    def log_event(
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Formats a security event as standardized structured JSON
        conforming to typical SIEM ingest schemas (e.g. CEF, Splunk, Elastic Common Schema).
        """
        payload = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "event.category": "security",
            "event.type": event_type,
            "log.level": severity,
            "message": description,
            "user.id": user_id,
            "client.ip": ip_address,
            "user_agent.original": user_agent,
            "security.details": details or {},
        }

        # Log at appropriate python log level based on event severity
        log_msg = f"[SECURITY_AUDIT] {json.dumps(payload)}"
        if severity == "CRITICAL":
            logger.critical(log_msg)
        elif severity == "HIGH":
            logger.error(log_msg)
        elif severity == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)


security_audit_logger = SecurityAuditLogger()
