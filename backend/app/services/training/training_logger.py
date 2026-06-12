import sys
import json
from datetime import datetime
from typing import Dict, Any


class TrainingLogger:
    @staticmethod
    def log(level: str, run_id: str, message: str, extra: Dict[str, Any] | None = None) -> None:
        """Emits a structured JSON log line to stdout."""
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "run_id": str(run_id),
            "message": message,
            "logger": "training_pipeline"
        }
        if extra:
            log_payload.update(extra)

        sys.stdout.write(json.dumps(log_payload) + "\n")
        sys.stdout.flush()

    def info(self, run_id: str, message: str, extra: Dict[str, Any] | None = None) -> None:
        self.log("INFO", run_id, message, extra)

    def warning(self, run_id: str, message: str, extra: Dict[str, Any] | None = None) -> None:
        self.log("WARNING", run_id, message, extra)

    def error(self, run_id: str, message: str, extra: Dict[str, Any] | None = None) -> None:
        self.log("ERROR", run_id, message, extra)


training_logger = TrainingLogger()
