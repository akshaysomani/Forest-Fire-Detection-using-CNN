import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import CompliancePolicy, ComplianceAudit, SecurityEvent
from app.services.security.policy_engine import policy_engine
from app.core.exceptions import ValidationException


class ComplianceManager:
    async def seed_compliance_policies(self, db: AsyncSession) -> None:
        """Seeds the standard compliance policies into the DB."""
        policies_def = {
            "SOC2": {
                "desc": "System and Organization Controls policy verifying platform logging, auditability, and access controls.",
                "category": "SOC2",
            },
            "GDPR": {
                "desc": "General Data Protection Regulation verifying data protection, user masking, and retention rules.",
                "category": "GDPR",
            },
        }

        for name, data in policies_def.items():
            q = select(CompliancePolicy).where(CompliancePolicy.name == name)
            res = await db.execute(q)
            if not res.scalar_one_or_none():
                policy = CompliancePolicy(name=name, description=data["desc"], category=data["category"], status="COMPLIANT")
                db.add(policy)
        await db.flush()

    async def run_compliance_check(
        self, db: AsyncSession, policy_name: str, checked_by_id: Optional[uuid.UUID] = None
    ) -> CompliancePolicy:
        """Run policy validation scan and update policy record compliance status."""
        q = select(CompliancePolicy).where(CompliancePolicy.name == policy_name)
        res = await db.execute(q)
        policy = res.scalar_one_or_none()

        if not policy:
            raise ValidationException(f"Compliance policy '{policy_name}' not found.")

        # Run engine validation
        if policy_name == "SOC2":
            report = await policy_engine.verify_soc2_compliance(db)
        elif policy_name == "GDPR":
            report = await policy_engine.verify_gdpr_compliance(db)
        else:
            raise ValidationException(f"Validation engine for policy '{policy_name}' is not registered.")

        # Update policy status
        new_status = "COMPLIANT" if report["compliant"] else "NON_COMPLIANT"
        policy.status = new_status
        policy.last_checked_at = datetime.utcnow()
        policy.details_json = report
        db.add(policy)

        # Log audit entry
        findings = ", ".join(report["issues"]) if report["issues"] else "All verification checks passed."
        audit = ComplianceAudit(
            policy_name=policy_name,
            checked_by_id=checked_by_id,
            status="PASS" if report["compliant"] else "FAIL",
            findings=findings,
            details_json=report,
        )
        db.add(audit)

        # Log warning if non-compliant
        if not report["compliant"]:
            event = SecurityEvent(
                event_type="COMPLIANCE_NON_COMPLIANCE_DETECTED",
                severity="HIGH",
                description=f"Compliance check failed for policy '{policy_name}': {findings}",
                user_id=checked_by_id,
                details_json=report,
            )
            db.add(event)

        await db.flush()
        return policy

    async def get_compliance_status(self, db: AsyncSession) -> List[CompliancePolicy]:
        """Returns the list of compliance policies and statuses."""
        q = select(CompliancePolicy)
        res = await db.execute(q)
        return list(res.scalars().all())


compliance_manager = ComplianceManager()
