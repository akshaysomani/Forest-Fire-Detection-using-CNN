import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import (
    RegisteredModel,
    ModelVersion,
    ModelDeployment,
    ModelApproval
)
from app.services.model_registry.model_metrics import ModelRegistryMetrics

logger = logging.getLogger("model_registry.model_registry_monitor")


class ModelRegistryMonitor:
    @staticmethod
    async def collect_registry_metrics(db: AsyncSession) -> ModelRegistryMetrics:
        """
        Queries model registry tables and aggregates operational metrics.
        """
        # 1. Total Model Families
        q_families = select(func.count()).select_from(RegisteredModel).where(RegisteredModel.deleted_at.is_(None))
        res_families = await db.execute(q_families)
        total_families = res_families.scalar() or 0

        # 2. Total Versions
        q_versions = select(func.count()).select_from(ModelVersion).where(ModelVersion.deleted_at.is_(None))
        res_versions = await db.execute(q_versions)
        total_versions = res_versions.scalar() or 0

        # 3. Active Deployments
        q_active_dep = select(func.count()).select_from(ModelDeployment).where(
            and_(ModelDeployment.status == "active", ModelDeployment.deleted_at.is_(None))
        )
        res_active_dep = await db.execute(q_active_dep)
        active_deployments = res_active_dep.scalar() or 0

        # 4. Staging vs Production
        q_staging_dep = select(func.count()).select_from(ModelDeployment).where(
            and_(
                ModelDeployment.environment == "staging",
                ModelDeployment.status == "active",
                ModelDeployment.deleted_at.is_(None)
            )
        )
        res_staging_dep = await db.execute(q_staging_dep)
        staging_deployments = res_staging_dep.scalar() or 0

        q_production_dep = select(func.count()).select_from(ModelDeployment).where(
            and_(
                ModelDeployment.environment == "production",
                ModelDeployment.status == "active",
                ModelDeployment.deleted_at.is_(None)
            )
        )
        res_production_dep = await db.execute(q_production_dep)
        production_deployments = res_production_dep.scalar() or 0

        # 5. Pending Approvals
        q_pending_app = select(func.count()).select_from(ModelApproval).where(
            and_(ModelApproval.status == "pending", ModelApproval.deleted_at.is_(None))
        )
        res_pending_app = await db.execute(q_pending_app)
        pending_approvals = res_pending_app.scalar() or 0

        # 6. State Distribution
        q_state = select(ModelVersion.status, func.count()).where(
            ModelVersion.deleted_at.is_(None)
        ).group_by(ModelVersion.status)
        res_state = await db.execute(q_state)
        state_distribution = {}
        for row in res_state.all():
            state_distribution[row[0]] = row[1]

        # Ensure all standard states exist in dict
        for state in ["Draft", "Training", "Validation", "Approved", "Staging", "Production", "Deprecated", "Archived"]:
            if state not in state_distribution:
                state_distribution[state] = 0

        # 7. Average Approval Time (in seconds)
        q_approved_times = select(ModelApproval.requested_at, ModelApproval.reviewed_at).where(
            and_(
                ModelApproval.status.in_(["approved", "rejected"]),
                ModelApproval.reviewed_at.is_not(None),
                ModelApproval.deleted_at.is_(None)
            )
        )
        res_approved_times = await db.execute(q_approved_times)
        total_time_seconds = 0.0
        count_processed = 0
        for req_at, rev_at in res_approved_times.all():
            diff = (rev_at - req_at).total_seconds()
            total_time_seconds += diff
            count_processed += 1
        
        avg_approval_time = (total_time_seconds / count_processed) if count_processed > 0 else 0.0

        # 8. Deployment Frequency (in days)
        # Simply calculate the average gap between deployments or default to 0
        q_deploy_times = select(ModelDeployment.deployed_at).where(
            ModelDeployment.deleted_at.is_(None)
        ).order_by(ModelDeployment.deployed_at.asc())
        res_deploy_times = await db.execute(q_deploy_times)
        deploy_times = [d[0] for d in res_deploy_times.all()]
        avg_deploy_gap_days = 0.0
        if len(deploy_times) > 1:
            gaps = [(deploy_times[i] - deploy_times[i - 1]).total_seconds() / 86400.0 for i in range(1, len(deploy_times))]
            avg_deploy_gap_days = sum(gaps) / len(gaps)

        return ModelRegistryMetrics(
            total_model_families=total_families,
            total_model_versions=total_versions,
            active_deployments=active_deployments,
            staging_deployments=staging_deployments,
            production_deployments=production_deployments,
            pending_approvals=pending_approvals,
            state_distribution=state_distribution,
            deployment_frequency_days=avg_deploy_gap_days,
            average_approval_time_seconds=avg_approval_time
        )


model_registry_monitor = ModelRegistryMonitor()
