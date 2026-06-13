import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("inference.observability")


class ObservabilityService:
    @staticmethod
    def log_inference_event(
        event_name: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "INFO"
    ) -> None:
        """
        Log structured log entries with metadata attributes.
        """
        log_msg = f"[{event_name}] {message}"
        extra_meta = metadata or {}

        if level.upper() == "INFO":
            logger.info(log_msg, extra={"metadata": extra_meta})
        elif level.upper() == "WARNING":
            logger.warning(log_msg, extra={"metadata": extra_meta})
        elif level.upper() == "ERROR":
            logger.error(log_msg, extra={"metadata": extra_meta})
        else:
            logger.debug(log_msg, extra={"metadata": extra_meta})

    @staticmethod
    def trigger_anomaly_alert(
        metric_name: str,
        threshold_value: Any,
        actual_value: Any,
        job_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Structured logger hook designed to notify operations teams about SLA breaches
        or high inference error rates.
        """
        alert_msg = (
            f"ALERT: Metric '{metric_name}' breached threshold of {threshold_value}. "
            f"Actual value: {actual_value}."
        )
        logger.critical(
            alert_msg,
            extra={
                "metric_name": metric_name,
                "threshold": threshold_value,
                "actual": actual_value,
                "details": job_details or {}
            }
        )


observability_service = ObservabilityService()
