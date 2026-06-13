import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentEvent, ResponseTeam, IncidentAssignment, IncidentStatusHistory, IncidentUpdate

logger = logging.getLogger("incident.response_tracking_service")


class ResponseTrackingService:
    async def get_system_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Computes system-wide operational KPIs:
        - Total incidents count (broken down by status & severity)
        - Average resolution time (seconds)
        - SLA compliance rate (%)
        - Active vs inactive vs on-break response teams count
        """
        # 1. Total Incidents by Status and Severity
        incident_q = select(Incident).where(Incident.deleted_at.is_(None))
        res = await db.execute(incident_q)
        incidents = res.scalars().all()

        total_count = len(incidents)
        status_counts = {}
        severity_counts = {}

        for inc in incidents:
            status_counts[inc.status] = status_counts.get(inc.status, 0) + 1
            severity_counts[inc.severity] = severity_counts.get(inc.severity, 0) + 1

        # 2. Average Resolution time & SLA breaches
        resolved_incidents = [inc for inc in incidents if inc.status in ["Resolved", "Closed"]]
        total_resolution_time = 0.0
        resolved_count = len(resolved_incidents)

        for inc in resolved_incidents:
            # Query history to find when it was resolved/closed
            history_q = (
                select(IncidentStatusHistory)
                .where(
                    and_(
                        IncidentStatusHistory.incident_id == inc.id,
                        IncidentStatusHistory.new_status.in_(["Resolved", "Closed"])
                    )
                )
                .order_by(IncidentStatusHistory.created_at.asc())
            )
            hist_res = await db.execute(history_q)
            hist_entry = hist_res.scalar_one_or_none()
            if hist_entry:
                end_time = hist_entry.created_at
            else:
                end_time = inc.updated_at

            start_time = inc.created_at
            duration = (end_time - start_time).total_seconds()
            total_resolution_time += max(0.0, duration)

        avg_resolution_time = (total_resolution_time / resolved_count) if resolved_count > 0 else 0.0

        # Calculate SLA breach rate (using SLATracker helper)
        from app.services.incident.sla_tracker import sla_tracker
        breached_count = 0
        current_time = datetime.now(timezone.utc)
        for inc in incidents:
            if sla_tracker.is_response_sla_breached(inc, current_time):
                breached_count += 1
            elif inc.status == "Escalated":
                breached_count += 1

        sla_compliance_rate = 100.0
        if total_count > 0:
            sla_compliance_rate = ((total_count - breached_count) / total_count) * 100.0

        # 3. Teams Status counts
        team_q = select(ResponseTeam).where(ResponseTeam.deleted_at.is_(None))
        team_res = await db.execute(team_q)
        teams = team_res.scalars().all()

        total_teams = len(teams)
        team_status_counts = {"Active": 0, "Inactive": 0, "On Break": 0}
        deployed_teams = 0

        for team in teams:
            team_status_counts[team.status] = team_status_counts.get(team.status, 0) + 1
            if team.current_incident_id is not None:
                deployed_teams += 1

        return {
            "total_incidents": total_count,
            "incidents_by_status": status_counts,
            "incidents_by_severity": severity_counts,
            "avg_resolution_time_seconds": avg_resolution_time,
            "sla_compliance_rate": round(sla_compliance_rate, 2),
            "total_teams": total_teams,
            "teams_by_status": team_status_counts,
            "teams_currently_deployed": deployed_teams
        }

    async def get_team_performance(self, db: AsyncSession, team_id: uuid.UUID) -> Dict[str, Any]:
        """
        Computes performance stats for a single team:
        - Total assignments count (Pending, Accepted, Rejected, Completed)
        - Average acknowledgment speed (seconds from dispatch to acceptance)
        - Total completed missions count
        """
        # Fetch team assignments
        q = select(IncidentAssignment).where(
            and_(
                IncidentAssignment.team_id == team_id,
                IncidentAssignment.deleted_at.is_(None)
            )
        )
        res = await db.execute(q)
        assignments = res.scalars().all()

        total_assignments = len(assignments)
        status_counts = {}
        ack_durations = []

        for assignment in assignments:
            status_counts[assignment.status] = status_counts.get(assignment.status, 0) + 1

            if assignment.status in ["Accepted", "Completed"]:
                # Query when it transitioned to Accepted or Accepted-equivalent
                # But wait, we can check IncidentEvent or status changes
                # Or we can just calculate time difference between accepted event and assignment.assigned_at
                event_q = select(IncidentEvent).where(
                    and_(
                        IncidentEvent.incident_id == assignment.incident_id,
                        IncidentEvent.event_type == "incident_assignment_accepted",
                        # Match team in payload if stored, or just closest event
                    )
                )
                event_res = await db.execute(event_q)
                event_entry = event_res.scalars().first()
                if event_entry:
                    ack_time = event_entry.created_at
                    dispatch_time = assignment.assigned_at
                    # Handle naive vs aware datetime objects safely
                    if ack_time.tzinfo is not None and dispatch_time.tzinfo is None:
                        dispatch_time = dispatch_time.replace(tzinfo=timezone.utc)
                    elif ack_time.tzinfo is None and dispatch_time.tzinfo is not None:
                        ack_time = ack_time.replace(tzinfo=timezone.utc)

                    duration = (ack_time - dispatch_time).total_seconds()
                    ack_durations.append(max(0.0, duration))

        avg_ack_speed = (sum(ack_durations) / len(ack_durations)) if ack_durations else 0.0

        return {
            "team_id": str(team_id),
            "total_assignments": total_assignments,
            "assignments_by_status": status_counts,
            "avg_acknowledgment_speed_seconds": avg_ack_speed,
            "completed_missions_count": status_counts.get("Completed", 0)
        }


response_tracking_service = ResponseTrackingService()
