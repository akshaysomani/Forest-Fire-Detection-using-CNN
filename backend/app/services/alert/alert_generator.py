import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection
from app.models.alert import Alert
from app.services.alert.alert_rules_service import alert_rules_service
from app.services.alert.severity_classifier import severity_classifier
from app.services.alert.risk_score_calculator import risk_score_calculator
from app.services.alert.alert_engine import alert_engine

logger = logging.getLogger("alert.alert_generator")


class AlertGenerator:
    async def evaluate_detection(self, db: AsyncSession, detection: Detection) -> Optional[Alert]:
        """
        Evaluate a prediction result to check if an alert needs to be generated.
        If threshold rules are met, trigger the alert engine.
        """
        # 1. Check if prediction is fire and meets confidence threshold
        should_trigger = alert_rules_service.should_raise_alert(
            prediction_label=detection.prediction_label, confidence=detection.confidence
        )

        if not should_trigger:
            logger.debug(f"Detection {detection.id} does not trigger alert rules.")
            return None

        # 2. Classify severity level
        severity = severity_classifier.classify(label=detection.prediction_label, confidence=detection.confidence)

        # 3. Calculate composite risk score
        risk_score = risk_score_calculator.calculate_score(
            label=detection.prediction_label,
            confidence=detection.confidence,
            latitude=detection.latitude,
            longitude=detection.longitude,
        )

        # 4. Format detailed alert message
        location_str = (
            f"at coordinates ({detection.latitude}, {detection.longitude})"
            if detection.latitude and detection.longitude
            else ""
        )
        message = (
            f"POTENTIAL WILDFIRE DETECTED: {detection.prediction_label.upper()} "
            f"identified with {detection.confidence * 100.0:.2f}% confidence {location_str}. "
            f"Composite Risk Score: {risk_score:.2f}/100.00."
        )

        # 5. Compile payload details
        payload = {
            "prediction_label": detection.prediction_label,
            "confidence": detection.confidence,
            "latitude": detection.latitude,
            "longitude": detection.longitude,
            "model_name": detection.model_name,
            "model_version": detection.model_version,
            "risk_score": risk_score,
            "image_path": detection.image_path,
            "filename": detection.filename,
        }

        # 6. Trigger alert creation and bus dispatch
        alert = await alert_engine.trigger_detection_alert(
            db=db, detection_id=detection.id, severity=severity, message=message, payload=payload
        )

        # 7. Update detection record state
        detection.alert_sent = True
        db.add(detection)
        await db.flush()

        logger.info(f"Alert successfully generated for detection {detection.id}. Alert ID: {alert.id}")
        return alert


alert_generator = AlertGenerator()
