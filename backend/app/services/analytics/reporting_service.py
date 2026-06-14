import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import ReportDefinition, ReportExecution, AnalyticsAuditLog
from app.schemas.analytics_schema import ReportDefinitionCreate, ReportGenerateRequest
from app.services.analytics.report_generator import report_generator
from app.services.analytics.export_service import export_service
from app.core.exceptions import EntityNotFoundException, AnalyticsException

logger = logging.getLogger("analytics.reporting_service")


class ReportingService:
    async def create_definition(self, db: AsyncSession, data: ReportDefinitionCreate, user_id: uuid.UUID) -> ReportDefinition:
        """Create a new report template/definition configuration."""
        definition = ReportDefinition(
            name=data.name,
            description=data.description,
            report_type=data.report_type,
            parameters=data.parameters,
            schedule_cron=data.schedule_cron,
            is_scheduled=data.is_scheduled,
            created_by=user_id,
        )
        db.add(definition)

        # Audit log
        audit = AnalyticsAuditLog(
            user_id=user_id, action="create_report_definition", details={"name": data.name, "report_type": data.report_type}
        )
        db.add(audit)
        await db.flush()
        return definition

    async def get_definitions(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ReportDefinition]:
        """List all active report definitions."""
        query = select(ReportDefinition).where(ReportDefinition.deleted_at.is_(None)).offset(skip).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_definition(self, db: AsyncSession, id: uuid.UUID) -> ReportDefinition:
        """Retrieve a specific report definition by ID."""
        query = select(ReportDefinition).where(and_(ReportDefinition.id == id, ReportDefinition.deleted_at.is_(None)))
        res = await db.execute(query)
        definition = res.scalar_one_or_none()
        if not definition:
            raise EntityNotFoundException("Report definition not found.")
        return definition

    async def delete_definition(self, db: AsyncSession, id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Soft delete a report definition."""
        definition = await self.get_definition(db, id)
        definition.deleted_at = datetime.now(timezone.utc)
        db.add(definition)

        # Audit log
        audit = AnalyticsAuditLog(user_id=user_id, action="delete_report_definition", details={"definition_id": str(id)})
        db.add(audit)
        await db.flush()

    async def execute_definition(self, db: AsyncSession, definition_id: uuid.UUID, user_id: uuid.UUID) -> ReportExecution:
        """Execute a report definition template."""
        definition = await self.get_definition(db, definition_id)
        return await self.generate_report(
            db=db,
            report_type=definition.report_type,
            export_format="PDF",
            parameters=definition.parameters,
            definition_id=definition.id,
            user_id=user_id,
        )

    async def generate_report(
        self,
        db: AsyncSession,
        report_type: str,
        export_format: str,
        parameters: Dict[str, Any],
        definition_id: uuid.UUID = None,
        user_id: uuid.UUID = None,
    ) -> ReportExecution:
        """Core report generation pipeline. Calculates metrics and formats a download file."""
        logger.info(f"Initiating report execution for {report_type} in {export_format} format...")
        start_time = time.time()

        # 1. Create running execution record
        execution = ReportExecution(
            report_definition_id=definition_id,
            report_type=report_type,
            executed_by=user_id,
            status="running",
            format=export_format.upper(),
            parameters=parameters,
        )
        db.add(execution)
        await db.flush()

        try:
            # 2. Extract report metrics rows
            report_data = await report_generator.generate_report_data(db, report_type, parameters)

            # 3. Stream data to export generator
            file_path = await export_service.generate_export(report_data, export_format.upper())

            # 4. Finalize execution success status
            execution.file_path = file_path
            execution.status = "completed"
            execution.execution_time_ms = int((time.time() - start_time) * 1000)

            # Audit log
            audit = AnalyticsAuditLog(
                user_id=user_id,
                action="generate_report",
                details={
                    "report_type": report_type,
                    "format": export_format,
                    "execution_id": str(execution.id),
                    "execution_time_ms": execution.execution_time_ms,
                },
            )
            db.add(audit)
            db.add(execution)
            await db.flush()
            logger.info(f"Report execution successfully completed in {execution.execution_time_ms} ms.")

        except Exception as e:
            logger.error(f"Error during report execution: {e}", exc_info=True)
            execution.status = "failed"
            execution.error_message = str(e)
            execution.execution_time_ms = int((time.time() - start_time) * 1000)
            db.add(execution)
            await db.flush()
            raise AnalyticsException(f"Failed to generate report: {str(e)}")

        return execution

    async def get_executions(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ReportExecution]:
        """Fetch list of all past report execution runs."""
        query = select(ReportExecution).order_by(ReportExecution.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_execution(self, db: AsyncSession, id: uuid.UUID) -> ReportExecution:
        """Fetch single report execution log by ID."""
        query = select(ReportExecution).where(ReportExecution.id == id)
        res = await db.execute(query)
        execution = res.scalar_one_or_none()
        if not execution:
            raise EntityNotFoundException("Report execution log not found.")
        return execution


reporting_service = ReportingService()
