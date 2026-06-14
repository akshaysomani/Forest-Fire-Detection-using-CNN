import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.user import User
from app.models.audit import AuditLog
from app.models.gis import Location, Region, Zone
from app.services.system_metrics import system_metrics
from app.repositories.dashboard_repository import dashboard_repository

logger = logging.getLogger("analytics.report_generator")


class ReportGenerator:
    async def generate_report_data(self, db: AsyncSession, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Compile raw reporting data based on report type and filter parameters."""
        logger.info(f"Generating report data for type: {report_type}")
        
        # Parse date filters
        start_date_str = parameters.get("start_date")
        end_date_str = parameters.get("end_date")
        
        start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00")) if start_date_str else datetime.now(timezone.utc) - datetime.timedelta(days=30)
        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00")) if end_date_str else datetime.now(timezone.utc)

        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": report_type,
            "parameters": parameters,
            "summary": {},
            "data": []
        }

        if report_type == "fire_detections":
            query = select(Detection).where(
                and_(
                    Detection.created_at.between(start_dt, end_dt),
                    Detection.deleted_at.is_(None)
                )
            )
            if "confidence" in parameters:
                query = query.where(Detection.confidence >= float(parameters["confidence"]))
            if "prediction_label" in parameters:
                query = query.where(Detection.prediction_label == parameters["prediction_label"])
            if "model_name" in parameters:
                query = query.where(Detection.model_name == parameters["model_name"])
            
            res = await db.execute(query)
            rows = res.scalars().all()
            
            result["summary"] = {
                "total_records": len(rows),
                "fire_count": sum(1 for r in rows if r.prediction_label == "fire"),
                "non_fire_count": sum(1 for r in rows if r.prediction_label == "non-fire"),
                "average_confidence": round(sum(r.confidence for r in rows) / len(rows), 4) if rows else 0.0
            }
            result["data"] = [
                {
                    "id": str(r.id),
                    "filename": r.filename,
                    "prediction_label": r.prediction_label,
                    "confidence": r.confidence,
                    "model_name": r.model_name,
                    "is_verified_fire": r.is_verified_fire,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "created_at": r.created_at.isoformat()
                }
                for r in rows
            ]

        elif report_type == "incidents":
            query = select(Incident).where(
                and_(
                    Incident.created_at.between(start_dt, end_dt),
                    Incident.deleted_at.is_(None)
                )
            )
            if "status" in parameters:
                query = query.where(Incident.status == parameters["status"])
            if "severity" in parameters:
                query = query.where(Incident.severity == parameters["severity"])
                
            res = await db.execute(query)
            rows = res.scalars().all()
            
            result["summary"] = {
                "total_incidents": len(rows),
                "active_count": sum(1 for r in rows if r.status not in ["Resolved", "Closed"]),
                "resolved_count": sum(1 for r in rows if r.status in ["Resolved", "Closed"]),
                "critical_count": sum(1 for r in rows if r.severity == "Critical")
            }
            result["data"] = [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "status": r.status,
                    "severity": r.severity,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "created_at": r.created_at.isoformat()
                }
                for r in rows
            ]

        elif report_type == "alerts":
            query = select(Alert).where(
                and_(
                    Alert.created_at.between(start_dt, end_dt),
                    Alert.deleted_at.is_(None)
                )
            )
            if "status" in parameters:
                query = query.where(Alert.status == parameters["status"])
            if "severity" in parameters:
                query = query.where(Alert.severity == parameters["severity"])
                
            res = await db.execute(query)
            rows = res.scalars().all()
            
            result["summary"] = {
                "total_alerts": len(rows),
                "active_alerts": sum(1 for r in rows if r.status == "active"),
                "acknowledged_alerts": sum(1 for r in rows if r.status == "acknowledged")
            }
            result["data"] = [
                {
                    "id": str(r.id),
                    "severity": r.severity,
                    "status": r.status,
                    "message": r.message,
                    "created_at": r.created_at.isoformat()
                }
                for r in rows
            ]

        elif report_type == "gis":
            # GIS summary statistics
            reg_q = select(Region).where(Region.deleted_at.is_(None))
            zone_q = select(Zone).where(Zone.deleted_at.is_(None))
            reg_res = await db.execute(reg_q)
            zone_res = await db.execute(zone_q)
            regions = reg_res.scalars().all()
            zones = zone_res.scalars().all()

            result["summary"] = {
                "total_regions": len(regions),
                "total_zones": len(zones),
                "extreme_risk_zones": sum(1 for z in zones if z.risk_level == "Extreme")
            }
            result["data"] = [
                {
                    "type": "zone",
                    "id": str(z.id),
                    "name": z.name,
                    "code": z.code,
                    "risk_level": z.risk_level,
                    "region_name": z.region.name if z.region else None
                }
                for z in zones
            ]

        elif report_type == "user_activity":
            query = select(AuditLog).where(
                AuditLog.created_at.between(start_dt, end_dt)
            )
            if "user_id" in parameters:
                query = query.where(AuditLog.user_id == uuid.UUID(parameters["user_id"]))
            if "action" in parameters:
                query = query.where(AuditLog.action == parameters["action"])
                
            res = await db.execute(query)
            rows = res.scalars().all()
            
            result["summary"] = {
                "total_activities": len(rows),
                "login_actions": sum(1 for r in rows if r.action == "user.login")
            }
            result["data"] = [
                {
                    "id": str(r.id),
                    "user_id": str(r.user_id) if r.user_id else None,
                    "action": r.action,
                    "ip_address": r.ip_address,
                    "resource_type": r.resource_type,
                    "created_at": r.created_at.isoformat()
                }
                for r in rows
            ]

        elif report_type == "system_health":
            cpu = system_metrics.get_cpu_usage_percent()
            ram = system_metrics.get_memory_usage()
            disk = system_metrics.get_storage_usage()
            active_sessions = await dashboard_repository.get_active_sessions_count(db)

            result["summary"] = {
                "cpu_usage_percent": cpu,
                "ram_usage_percent": ram["percentage_used"],
                "disk_usage_percent": disk["percentage_used"],
                "active_sessions": active_sessions
            }
            result["data"] = [
                {
                    "metric": "cpu",
                    "value": cpu,
                    "details": {}
                },
                {
                    "metric": "ram",
                    "value": ram["percentage_used"],
                    "details": ram
                },
                {
                    "metric": "disk",
                    "value": disk["percentage_used"],
                    "details": disk
                }
            ]
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        return result


report_generator = ReportGenerator()
