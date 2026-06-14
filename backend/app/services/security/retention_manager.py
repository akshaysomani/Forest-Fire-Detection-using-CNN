from datetime import datetime, timedelta
from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import DataRetentionLog, SecurityEvent


class RetentionManager:
    async def run_data_retention_pruning(self, db: AsyncSession) -> dict:
        """
        Executes data pruning queries based on retention settings:
        - Audit logs (pruned after 180 days)
        - Security events (pruned after 90 days)
        - Observability logs (pruned after 30 days)
        """
        now = datetime.utcnow()
        pruned_records = {}
        status = "SUCCESS"
        error_msg = None

        retention_settings = {"audit_logs": 180, "security_events": 90, "observability_logs": 30}

        try:
            for table, days in retention_settings.items():
                threshold = now - timedelta(days=days)

                # Dynamic deletion using raw execution since some tables don't use soft delete or to purge permanently
                if table == "security_events":
                    q = text(f"DELETE FROM {table} WHERE timestamp < :threshold")
                    res = await db.execute(q, {"threshold": threshold})
                elif table == "observability_logs":
                    q = text(f"DELETE FROM {table} WHERE timestamp < :threshold")
                    res = await db.execute(q, {"threshold": threshold})
                else:
                    # audit_logs
                    q = text(f"DELETE FROM {table} WHERE created_at < :threshold")
                    res = await db.execute(q, {"threshold": threshold})

                deleted_count = res.rowcount or 0
                pruned_records[table] = deleted_count

                # Log individual table deletion
                log = DataRetentionLog(
                    table_name=table,
                    records_pruned=deleted_count,
                    status="SUCCESS",
                    details_json={"threshold_date": threshold.isoformat(), "retention_days": days},
                )
                db.add(log)

            await db.flush()

        except Exception as e:
            status = "FAILURE"
            error_msg = str(e)
            # Log failure
            log = DataRetentionLog(table_name="ALL", records_pruned=0, status="FAILURE", details_json={"error": error_msg})
            db.add(log)
            await db.flush()

        return {"status": status, "pruned": pruned_records, "error": error_msg}


retention_manager = RetentionManager()
