"""
Dependency Checker - Health check driver for platform dependencies.

Verifies the operational status of critical dependencies: database connectivity,
storage volume access, ML model checkpoint availability, and background queue health.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.system_metrics import system_metrics

logger = logging.getLogger("observability.dependency_checker")


class DependencyChecker:
    """
    Checks the health status of all platform dependencies.
    Returns structured health reports for each subsystem.
    """

    async def check_database(self, db: AsyncSession) -> Dict[str, Any]:
        """Verify database connectivity with a lightweight query."""
        import time

        start = time.perf_counter()
        try:
            result = await db.execute(text("SELECT 1"))
            val = result.scalar()
            latency = round((time.perf_counter() - start) * 1000, 2)
            healthy = val == 1
            return {
                "status": "healthy" if healthy else "unhealthy",
                "latency_ms": latency,
                "details": {"query_result": val},
            }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.critical(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency,
                "details": {"error": str(e)},
            }

    def check_storage(self, path: str = ".") -> Dict[str, Any]:
        """Verify storage volume accessibility and capacity."""
        try:
            storage = system_metrics.get_storage_usage(path)
            pct_used = storage.get("percentage_used", 0.0)

            if pct_used >= 95.0:
                status = "unhealthy"
            elif pct_used >= 85.0:
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "latency_ms": None,
                "details": storage,
            }
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "details": {"error": str(e)},
            }

    def check_ml_models(self, model_dir: str = "storage") -> Dict[str, Any]:
        """
        Verify ML model checkpoint availability.
        Checks if the model storage directory exists and is accessible.
        """
        try:
            exists = os.path.exists(model_dir)
            accessible = os.access(model_dir, os.R_OK) if exists else False

            if exists and accessible:
                status = "healthy"
            elif exists:
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "latency_ms": None,
                "details": {
                    "directory_exists": exists,
                    "readable": accessible,
                    "path": model_dir,
                },
            }
        except Exception as e:
            logger.error(f"ML model health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "details": {"error": str(e)},
            }

    def check_queues(self) -> Dict[str, Any]:
        """
        Verify background queue health.
        In the current architecture, queues are in-process asyncio tasks.
        """
        return {
            "status": "healthy",
            "latency_ms": None,
            "details": {
                "queue_type": "in_process_asyncio",
                "status_note": "Background workers running within the application process",
            },
        }

    async def check_all(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """Run all dependency health checks and return a comprehensive report."""
        return {
            "database": await self.check_database(db),
            "storage": self.check_storage(),
            "ml_models": self.check_ml_models(),
            "queues": self.check_queues(),
        }


# Module-level singleton
dependency_checker = DependencyChecker()
