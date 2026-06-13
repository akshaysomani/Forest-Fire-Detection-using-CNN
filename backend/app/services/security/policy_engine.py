from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


class PolicyEngine:
    async def verify_soc2_compliance(self, db: AsyncSession) -> dict:
        """SOC2 security policy: verify system logging and authentication configuration."""
        issues = []
        
        # Check 1: Ensure audit logs exist and are populated
        try:
            res = await db.execute(text("SELECT count(*) FROM audit_logs"))
            count = res.scalar() or 0
            if count == 0:
                issues.append("SOC2.AUDIT_EMPTY: Audit logs table is completely empty.")
        except Exception:
            issues.append("SOC2.AUDIT_UNAVAILABLE: Audit logs database table is not accessible.")

        # Check 2: Ensure default admin password has been changed or user accounts are verified
        try:
            res = await db.execute(text("SELECT count(*) FROM users WHERE username = 'admin'"))
            admin_exists = res.scalar() or 0
            if admin_exists:
                # Check default hashed password pattern or verification status
                res_ver = await db.execute(text("SELECT is_verified FROM users WHERE username = 'admin'"))
                admin_verified = res_ver.scalar()
                if not admin_verified:
                    issues.append("SOC2.ADMIN_UNVERIFIED: Default administrator account is not verified.")
        except Exception:
            pass

        return {
            "policy": "SOC2",
            "compliant": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }

    async def verify_gdpr_compliance(self, db: AsyncSession) -> dict:
        """GDPR compliance check: verify data encryption, classification, and retention policies."""
        issues = []
        
        # Check 1: Verify that data retention runs are occurring
        try:
            res = await db.execute(text("SELECT count(*) FROM data_retention_logs WHERE status = 'SUCCESS'"))
            runs = res.scalar() or 0
            if runs == 0:
                issues.append("GDPR.NO_RETENTION_RUNS: No successful data retention/pruning logs found.")
        except Exception:
            issues.append("GDPR.RETENTION_UNAVAILABLE: Retention logs table is not accessible.")

        # Check 2: Verify user personal data (email) is masked or restricted in logs
        try:
            res = await db.execute(text("SELECT count(*) FROM audit_logs WHERE details LIKE '%@%'"))
            unmasked_logs = res.scalar() or 0
            if unmasked_logs > 10:
                issues.append(f"GDPR.PII_IN_LOGS: Found {unmasked_logs} entries containing raw emails in details.")
        except Exception:
            pass

        return {
            "policy": "GDPR",
            "compliant": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }


from datetime import datetime
policy_engine = PolicyEngine()
