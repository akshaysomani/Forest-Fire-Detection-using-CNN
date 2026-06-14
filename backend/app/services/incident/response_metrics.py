import logging
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident

logger = logging.getLogger("incident.response_metrics")


class ResponseMetrics:
    def compile_resolution_distribution(self, incidents: List[Incident]) -> Dict[str, Any]:
        """Categorizes resolved incidents by severity and provides average resolution speed."""
        distribution = {}
        for inc in incidents:
            if inc.status in ["Resolved", "Closed"]:
                sev = inc.severity
                if sev not in distribution:
                    distribution[sev] = {"resolved_count": 0, "average_duration_hours": 0.0}
                distribution[sev]["resolved_count"] += 1
                # Simplified check for testing
                duration_hours = max(0.1, (inc.updated_at - inc.created_at).total_seconds() / 3600.0)
                distribution[sev]["average_duration_hours"] += duration_hours

        for sev, data in distribution.items():
            if data["resolved_count"] > 0:
                data["average_duration_hours"] = round(data["average_duration_hours"] / data["resolved_count"], 2)

        return distribution


response_metrics = ResponseMetrics()
