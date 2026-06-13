"""
SLO Service - Evaluates Service Level Objectives and persists compliance records.

Computes daily/weekly success rates from PerformanceMetric data,
evaluates SLO compliance against SLI targets, and tracks remaining error budgets.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import PerformanceMetric, SloCompliance
from app.services.observability.sli_manager import sli_manager

logger = logging.getLogger("observability.slo_service")


class SLOService:
    """
    Evaluates and records Service Level Objective compliance.
    Computes success rates from performance data and persists compliance records.
    """

    async def evaluate_api_availability(
        self,
        db: AsyncSession,
        window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate API availability as percentage of non-5xx responses.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]

        total_q = select(func.count(PerformanceMetric.id)).where(and_(*conditions))
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        success_q = select(func.count(PerformanceMetric.id)).where(
            and_(*conditions, PerformanceMetric.status_code < 500)
        )
        success_result = await db.execute(success_q)
        success = success_result.scalar() or 0

        actual_pct = (success / max(total, 1)) * 100.0
        return sli_manager.evaluate_compliance("api_availability", actual_pct)

    async def evaluate_latency_slo(
        self,
        db: AsyncSession,
        window_days: int = 7,
        threshold_ms: float = 500.0,
    ) -> Dict[str, Any]:
        """
        Calculate the percentage of requests under the latency threshold.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]

        total_q = select(func.count(PerformanceMetric.id)).where(and_(*conditions))
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        fast_q = select(func.count(PerformanceMetric.id)).where(
            and_(*conditions, PerformanceMetric.latency_ms <= threshold_ms)
        )
        fast_result = await db.execute(fast_q)
        fast = fast_result.scalar() or 0

        actual_pct = (fast / max(total, 1)) * 100.0
        return sli_manager.evaluate_compliance("api_latency_p95", actual_pct)

    async def evaluate_error_rate_slo(
        self,
        db: AsyncSession,
        window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate the percentage of requests without server errors (5xx).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]

        total_q = select(func.count(PerformanceMetric.id)).where(and_(*conditions))
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        non_error_q = select(func.count(PerformanceMetric.id)).where(
            and_(*conditions, PerformanceMetric.status_code < 500)
        )
        non_error_result = await db.execute(non_error_q)
        non_errors = non_error_result.scalar() or 0

        actual_pct = (non_errors / max(total, 1)) * 100.0
        return sli_manager.evaluate_compliance("error_rate", actual_pct)

    async def evaluate_all_slos(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Evaluate all registered SLOs and return a comprehensive compliance report.
        """
        availability = await self.evaluate_api_availability(db)
        latency = await self.evaluate_latency_slo(db)
        error_rate = await self.evaluate_error_rate_slo(db)

        evaluations = {
            "api_availability": availability,
            "api_latency_p95": latency,
            "error_rate": error_rate,
        }

        # Compute overall compliance
        all_compliant = all(e.get("compliant", False) for e in evaluations.values())

        # Compute error budgets summary
        error_budgets = {}
        for key, evaluation in evaluations.items():
            error_budgets[key] = evaluation.get("error_budget_remaining", 0.0)

        return {
            "evaluations": evaluations,
            "overall_compliant": all_compliant,
            "error_budgets": error_budgets,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def record_compliance(
        self,
        db: AsyncSession,
        slo_name: str,
        target_percentage: float,
        actual_percentage: float,
        window_days: int,
        compliant: bool,
    ) -> SloCompliance:
        """Persist an SLO compliance record to the database."""
        record = SloCompliance(
            slo_name=slo_name,
            target_percentage=target_percentage,
            actual_percentage=round(actual_percentage, 4),
            window_days=window_days,
            compliant=compliant,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.flush()
        return record

    async def get_compliance_history(
        self,
        db: AsyncSession,
        slo_name: str = None,
        limit: int = 30,
    ) -> List[SloCompliance]:
        """Retrieve recent SLO compliance records."""
        conditions = [SloCompliance.deleted_at.is_(None)]
        if slo_name:
            conditions.append(SloCompliance.slo_name == slo_name)

        query = (
            select(SloCompliance)
            .where(and_(*conditions))
            .order_by(desc(SloCompliance.timestamp))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


# Module-level singleton
slo_service = SLOService()
