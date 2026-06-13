import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.incident.response_tracking_service import response_tracking_service
from app.services.incident.incident_metrics import incident_metrics
from app.services.incident.performance_tracker import performance_tracker
from app.services.incident.incident_monitor import incident_monitor

logger = logging.getLogger("incident.incident_observability_service")


class IncidentObservabilityService:
    async def get_observability_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Gathers KPIs, active incident ratios, specialty performance statistics,
        chronological timelines, and in-memory counters to return a single
        dashboard payload.
        """
        logger.info("Compiling dashboard observability metrics for incidents...")
        
        system_kpis = await response_tracking_service.get_system_kpis(db)
        ratios = await incident_metrics.get_active_ratios(db)
        timeline = await incident_metrics.get_timeline_metrics(db, days=7)
        specialties = await performance_tracker.get_specialty_performance(db)
        in_memory = incident_monitor.get_in_memory_metrics()

        return {
            "kpis": system_kpis,
            "active_ratios": ratios,
            "timeline_trends": timeline,
            "specialty_performance": specialties,
            "in_memory_counters": in_memory
        }


incident_observability_service = IncidentObservabilityService()
