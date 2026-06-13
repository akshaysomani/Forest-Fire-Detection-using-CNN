import pytest
from app.services.security.threat_detection_engine import threat_detection_engine


def test_sql_injection_payload_detection():
    """Assert threat detection engine blocks SQL Injection payload keywords."""
    payloads = [
        "1' OR '1'='1",
        "UNION SELECT username, password FROM users",
        "'; DROP TABLE detections; --",
    ]
    for payload in payloads:
        is_threat, threat_type = threat_detection_engine.detect_threat(
            method="GET",
            path="/api/v1/predict",
            query_params=payload,
            headers={},
            body=""
        )
        assert is_threat is True
        assert "SQL_INJECTION" in threat_type


def test_xss_payload_detection():
    """Assert threat detection engine blocks Cross-Site Scripting payload snippets."""
    payloads = [
        "<script>alert('exploit')</script>",
        "javascript:void(0)",
        "<img src=x onerror=alert(1)>",
        "<svg onload=javascript:alert(1)>",
    ]
    for payload in payloads:
        is_threat, threat_type = threat_detection_engine.detect_threat(
            method="GET",
            path="/api/v1/predict",
            query_params=payload,
            headers={},
            body=""
        )
        assert is_threat is True
        assert "XSS" in threat_type


def test_safe_content_detection():
    """Assert normal parameters are not flagged as exploits (False Positives validation)."""
    safe_strings = [
        "Select correct region from the list",
        "Ranger report on fire observations",
        "Active fire contained in zone A",
    ]
    for s in safe_strings:
        is_threat, threat_type = threat_detection_engine.detect_threat(
            method="GET",
            path="/api/v1/predict",
            query_params=s,
            headers={},
            body=""
        )
        assert is_threat is False

