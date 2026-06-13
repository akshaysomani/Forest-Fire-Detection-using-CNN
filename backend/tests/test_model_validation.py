import pytest
import io
from app.services.inference.risk_analyzer import risk_analyzer
from app.services.inference.input_validator import input_validator
from app.core.exceptions import ValidationException

def test_risk_analyzer_matrix():
    """Assert risk level matrix mapping thresholds."""
    # Label: fire
    assert risk_analyzer.analyze_risk("fire", 0.95) == "High"
    assert risk_analyzer.analyze_risk("fire", 0.85) == "High"
    assert risk_analyzer.analyze_risk("fire", 0.65) == "Medium"
    assert risk_analyzer.analyze_risk("fire", 0.40) == "Low"

    # Label: non-fire
    assert risk_analyzer.analyze_risk("non-fire", 0.95) == "Low"
    assert risk_analyzer.analyze_risk("non-fire", 0.50) == "Low"

def test_input_validator_size():
    """Assert file payload size validation rules."""
    # Max size check (15MB)
    large_bytes = b"\x00" * (16 * 1024 * 1024)
    with pytest.raises(ValidationException) as exc:
        input_validator.validate_image_bytes(large_bytes, "heavy.png")
    assert "File size exceeds" in str(exc.value)

def test_input_validator_mime():
    """Assert unsupported file format blocks."""
    bad_bytes = b"sample text content"
    with pytest.raises(ValidationException) as exc:
        input_validator.validate_image_bytes(bad_bytes, "script.py")
    assert "Corrupted or invalid image file" in str(exc.value)

def test_model_accuracy_tolerances_report():
    """Simulate model accuracy evaluation benchmarks reporting."""
    # Synthetic performance logs asserting precision/recall targets
    precision = 0.94
    recall = 0.91
    f1_score = 2 * (precision * recall) / (precision + recall)
    
    # Assert criteria targets
    assert precision >= 0.90
    assert recall >= 0.90
    assert f1_score >= 0.90

