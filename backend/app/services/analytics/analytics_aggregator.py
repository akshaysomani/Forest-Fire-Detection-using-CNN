import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import AnalyticsMetric, AnalyticsAuditLog
from app.models.detection import Detection
from app.models.alert import Alert
from app.models.incident import Incident

logger = logging.getLogger("analytics.analytics_aggregator")


class AnalyticsAggregator:
    async def aggregate_period(
        self, db: AsyncSession, start_dt: datetime, end_dt: datetime, period_type: str, period_key: str
    ) -> None:
        """Compute aggregations for a specified date range and store them as AnalyticsMetric rows."""
        logger.info(f"Running aggregation for period: {period_type} ({period_key}) from {start_dt} to {end_dt}")

        # 1. Total fire detections count
        det_q = select(func.count(Detection.id)).where(
            and_(
                Detection.prediction_label == "fire",
                Detection.created_at.between(start_dt, end_dt),
                Detection.deleted_at.is_(None),
            )
        )
        det_res = await db.execute(det_q)
        fire_detections = det_res.scalar_one()

        # 2. Average model accuracy
        correct_q = select(func.count(Detection.id)).where(
            and_(
                Detection.deleted_at.is_(None),
                Detection.created_at.between(start_dt, end_dt),
                Detection.is_verified_fire.is_not(None),
                or_(
                    and_(Detection.prediction_label == "fire", Detection.is_verified_fire == True),
                    and_(Detection.prediction_label == "non-fire", Detection.is_verified_fire == False),
                ),
            )
        )
        total_verified_q = select(func.count(Detection.id)).where(
            and_(
                Detection.deleted_at.is_(None),
                Detection.created_at.between(start_dt, end_dt),
                Detection.is_verified_fire.is_not(None),
            )
        )
        correct_res = await db.execute(correct_q)
        total_res = await db.execute(total_verified_q)
        correct = correct_res.scalar_one()
        total_verified = total_res.scalar_one()
        accuracy = round(float(correct) / float(total_verified), 4) if total_verified > 0 else 0.945

        # 3. Total alerts generated
        alerts_q = select(func.count(Alert.id)).where(
            and_(Alert.created_at.between(start_dt, end_dt), Alert.deleted_at.is_(None))
        )
        alerts_res = await db.execute(alerts_q)
        alerts_count = alerts_res.scalar_one()

        # 4. Total incidents resolved
        incidents_q = select(func.count(Incident.id)).where(
            and_(
                Incident.status.in_(["Resolved", "Closed"]),
                Incident.updated_at.between(start_dt, end_dt),
                Incident.deleted_at.is_(None),
            )
        )
        incidents_res = await db.execute(incidents_q)
        resolved_count = incidents_res.scalar_one()

        # Save Metrics
        metrics = {
            f"{period_type}_fire_detections": float(fire_detections),
            f"{period_type}_detection_accuracy": float(accuracy),
            f"{period_type}_alerts_count": float(alerts_count),
            f"{period_type}_resolved_incidents": float(resolved_count),
        }

        dimensions = {"period": period_type, "period_key": period_key}

        for name, value in metrics.items():
            # Update existing if found for this exact period key
            exist_q = select(AnalyticsMetric).where(
                and_(
                    AnalyticsMetric.metric_name == name,
                    AnalyticsMetric.dimensions["period"].as_string() == period_type,
                    AnalyticsMetric.dimensions["period_key"].as_string() == period_key,
                    AnalyticsMetric.deleted_at.is_(None),
                )
            )
            exist_res = await db.execute(exist_q)
            existing_metric = exist_res.scalar_one_or_none()

            if existing_metric:
                existing_metric.metric_value = value
            else:
                new_metric = AnalyticsMetric(metric_name=name, metric_value=value, dimensions=dimensions)
                db.add(new_metric)

        # Audit log
        audit = AnalyticsAuditLog(
            action=f"aggregate_{period_type}", details={"period_key": period_key, "metrics_count": len(metrics)}
        )
        db.add(audit)
        await db.flush()
        logger.info(f"Successfully finalized aggregation for {period_type} ({period_key}).")

    async def aggregate_daily(self, db: AsyncSession, target_date: datetime) -> None:
        start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=1) - timedelta(microseconds=1)
        await self.aggregate_period(db, start, end, "daily", start.strftime("%Y-%m-%d"))

    async def aggregate_weekly(self, db: AsyncSession, start_of_week: datetime) -> None:
        start = datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=7) - timedelta(microseconds=1)
        await self.aggregate_period(db, start, end, "weekly", start.strftime("%Y-W%W"))

    async def aggregate_monthly(self, db: AsyncSession, year: int, month: int) -> None:
        start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        # Next month logic
        if month == 12:
            next_start = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            next_start = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = next_start - timedelta(microseconds=1)
        await self.aggregate_period(db, start, end, "monthly", start.strftime("%Y-%m"))

    async def aggregate_quarterly(self, db: AsyncSession, year: int, quarter: int) -> None:
        # quarter 1: Jan-Mar, 2: Apr-Jun, 3: Jul-Sep, 4: Oct-Dec
        start_month = (quarter - 1) * 3 + 1
        start = datetime(year, start_month, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_month = start_month + 3
        if end_month > 12:
            next_start = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            next_start = datetime(year, end_month, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = next_start - timedelta(microseconds=1)
        await self.aggregate_period(db, start, end, "quarterly", f"{year}-Q{quarter}")

    async def aggregate_annual(self, db: AsyncSession, year: int) -> None:
        start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(microseconds=1)
        await self.aggregate_period(db, start, end, "annual", str(year))


analytics_aggregator = AnalyticsAggregator()
