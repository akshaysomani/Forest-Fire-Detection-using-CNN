from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import CompliancePolicy, ComplianceAudit, DataRetentionLog


class ComplianceReportingEngine:
    async def generate_executive_compliance_report(self, db: AsyncSession) -> dict:
        """Compile a formal compliance audit summary report."""
        q_policies = select(CompliancePolicy)
        res_policies = await db.execute(q_policies)
        policies = res_policies.scalars().all()

        compliant_count = sum(1 for p in policies if p.status == "COMPLIANT")
        total_policies = len(policies)
        compliance_percentage = (compliant_count / total_policies * 100.0) if total_policies > 0 else 100.0

        # Fetch recent retention log
        q_ret = select(DataRetentionLog).order_by(DataRetentionLog.execution_date.desc()).limit(5)
        res_ret = await db.execute(q_ret)
        retention_runs = list(res_ret.scalars().all())

        # Compile policy detail audits
        policy_details = []
        for p in policies:
            policy_details.append({
                "policy_name": p.name,
                "category": p.category,
                "status": p.status,
                "last_checked": p.last_checked_at.isoformat(),
                "findings": p.details_json.get("issues", []) if p.details_json else []
            })

        return {
            "compliance_percentage": compliance_percentage,
            "total_policies_scanned": total_policies,
            "compliant_policies_count": compliant_count,
            "non_compliant_policies_count": total_policies - compliant_count,
            "retention_status": {
                "total_pruning_runs": len(retention_runs),
                "last_run": retention_runs[0].execution_date.isoformat() if retention_runs else None
            },
            "policies": policy_details
        }


compliance_reporting_engine = ComplianceReportingEngine()
