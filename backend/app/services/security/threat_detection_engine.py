import re
from typing import Dict, Any, Tuple


class ThreatDetectionEngine:
    def __init__(self):
        # Threat signature patterns
        self._sqli_patterns = [
            re.compile(r"union\s+select", re.IGNORECASE),
            re.compile(r"'\s*or\s+\d+\s*=\s*\d+", re.IGNORECASE),
            re.compile(r"'\s*or\s*'\w*'\s*=\s*'\w*", re.IGNORECASE),
            re.compile(r"'\s*and\s+\d+\s*=\s*\d+", re.IGNORECASE),
            re.compile(r"'\s*and\s*'\w*'\s*=\s*'\w*", re.IGNORECASE),
            re.compile(r"';\s*--", re.IGNORECASE),
            re.compile(r"';\s*drop\s+table", re.IGNORECASE),
            re.compile(r"';\s*delete\s+from", re.IGNORECASE),
            re.compile(r"';\s*insert\s+into", re.IGNORECASE),
        ]

        self._xss_patterns = [
            re.compile(r"<script.*?>", re.IGNORECASE),
            re.compile(r"javascript\s*:", re.IGNORECASE),
            re.compile(r"onerror\s*=", re.IGNORECASE),
            re.compile(r"onload\s*=", re.IGNORECASE),
            re.compile(r"<iframe.*?>", re.IGNORECASE),
            re.compile(r"<svg.*?>", re.IGNORECASE),
            re.compile(r"alert\s*\(.*?\)", re.IGNORECASE),
        ]

        self._traversal_patterns = [
            re.compile(r"\.\./", re.IGNORECASE),
            re.compile(r"\.\.\\", re.IGNORECASE),
            re.compile(r"/etc/passwd", re.IGNORECASE),
            re.compile(r"windows/win\.ini", re.IGNORECASE),
            re.compile(r"cmd\.exe", re.IGNORECASE),
        ]

    def detect_threat(self, method: str, path: str, query_params: str, headers: Dict[str, str], body: str) -> Tuple[bool, str]:
        """
        Scan path, query strings, headers, and request body for common attack signatures.
        Returns (is_threat, threat_type).
        """
        payloads = [("PATH", path), ("QUERY", query_params), ("BODY", body)]

        # Scan headers
        for k, v in headers.items():
            if k.lower() in ["user-agent", "x-forwarded-for", "authorization"]:
                payloads.append((f"HEADER_{k.upper()}", v))

        for source, text in payloads:
            if not text:
                continue

            # SQL Injection check
            for pattern in self._sqli_patterns:
                if pattern.search(text):
                    return True, f"SQL_INJECTION_DETECTION ({source})"

            # XSS check
            for pattern in self._xss_patterns:
                if pattern.search(text):
                    return True, f"XSS_DETECTION ({source})"

            # Path Traversal check
            for pattern in self._traversal_patterns:
                if pattern.search(text):
                    return True, f"PATH_TRAVERSAL_DETECTION ({source})"

        return False, ""


threat_detection_engine = ThreatDetectionEngine()
