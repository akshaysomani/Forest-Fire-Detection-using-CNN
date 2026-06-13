import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.security import (
    AccessReviewCampaign,
    AccessReviewDecision,
    SecretMetadata,
    SecretRotationLog,
    SecurityEvent,
    CompliancePolicy,
    ComplianceAudit,
    DataRetentionLog
)
from app.services.password_service import password_service
from app.services.security.encryption_manager import encryption_manager
from app.services.security.data_classification_service import data_classification_service
from app.services.security.data_protection_service import data_protection_service
from app.services.security.threat_detection_engine import threat_detection_engine
from app.services.security.api_security_service import api_security_service
from app.services.security.identity_governance_service import identity_governance_service
from app.services.security.access_review_manager import access_review_manager
from app.services.security.permission_auditor import permission_auditor
from app.services.security.secret_manager import secret_manager
from app.services.security.credential_rotation_service import credential_rotation_service
from app.services.security.secret_audit_service import secret_audit_service
from app.services.security.security_event_service import security_event_service
from app.services.security.security_incident_tracker import security_incident_tracker
from app.services.security.policy_engine import policy_engine
from app.services.security.retention_manager import retention_manager
from app.services.security.compliance_manager import compliance_manager
from app.services.security.risk_engine import risk_engine
from app.services.security.threat_analyzer import threat_analyzer
from app.services.security.governance_dashboard_service import governance_dashboard_service

pytestmark = pytest.mark.asyncio


# ─── Test Helpers ─────────────────────────────────────────────────────────────


async def get_auth_headers(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "Password123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_user_with_role(db: AsyncSession, username: str, role_name: str) -> User:
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role = res.scalar_one_or_none()

    if not role:
        # Create default role if missing
        role = Role(name=role_name, description=f"{role_name} role")
        db.add(role)
        await db.flush()

    user = User(
        email=f"{username}@forestfire.org",
        username=username,
        hashed_password=password_service.hash_password("Password123!"),
        is_active=True,
        is_verified=True,
    )
    user.roles.append(role)
    db.add(user)
    await db.flush()
    return user


# ─── Unit Tests: Encryption & Classification ───────────────────────────────────


async def test_encryption_manager_round_trip():
    """Test that EncryptionManager correctly encrypts and decrypts values."""
    plain = "SuperConfidentialCoordinateValue"
    cipher = encryption_manager.encrypt(plain)
    assert cipher != plain
    assert encryption_manager.decrypt(cipher) == plain


async def test_data_classification_masking():
    """Test that DataClassificationService accurately flags and masks confidential strings."""
    assert data_classification_service.get_field_classification("user", "email") == "CONFIDENTIAL"
    assert data_classification_service.get_field_classification("user", "hashed_password") == "RESTRICTED"

    email = "officer@forestfire.org"
    masked_email = data_classification_service.mask_value("email", email)
    assert masked_email != email
    assert masked_email == "o***@forestfire.org"

    phone = "+1234567890"
    masked_phone = data_classification_service.mask_value("phone", phone)
    assert "****" in masked_phone


# ─── Unit Tests: Threat Detection Engine ──────────────────────────────────────


async def test_threat_detection_engine_patterns():
    """Test that common web attacks are successfully caught by the threat engine."""
    # SQLi attack
    is_sqli, threat_type = threat_detection_engine.detect_threat(
        "POST", "/api/v1/auth/login", "", {}, "username=admin' or '1'='1"
    )
    assert is_sqli is True
    assert "SQL_INJECTION" in threat_type

    # XSS attack
    is_xss, threat_type = threat_detection_engine.detect_threat(
        "GET", "/api/v1/incidents", "search=<script>alert('hack')</script>", {}, ""
    )
    assert is_xss is True
    assert "XSS" in threat_type

    # Path Traversal attack
    is_traversal, threat_type = threat_detection_engine.detect_threat(
        "GET", "/api/v1/datasets/download", "file=../../../../etc/passwd", {}, ""
    )
    assert is_traversal is True
    assert "PATH_TRAVERSAL" in threat_type

    # Safe request
    is_safe, threat_type = threat_detection_engine.detect_threat(
        "POST", "/api/v1/incidents", "", {}, "title=Active Fire Region 5&severity=HIGH"
    )
    assert is_safe is False
    assert threat_type == ""


# ─── Unit Tests: API Security Service ─────────────────────────────────────────


async def test_api_security_service_blocking_and_rate_limits():
    """Test IP blacklist tracking and request rate-limiting simulation."""
    api_security_service.unblock_ip("192.168.1.100")
    assert api_security_service.is_ip_blocked("192.168.1.100") is False

    # Block IP
    api_security_service.block_ip("192.168.1.100")
    assert api_security_service.is_ip_blocked("192.168.1.100") is True

    # Unblock
    api_security_service.unblock_ip("192.168.1.100")
    assert api_security_service.is_ip_blocked("192.168.1.100") is False

    # Trigger rate limit block (requires 100 requests)
    for _ in range(101):
        api_security_service.check_rate_limit("192.168.1.200")
    assert api_security_service.is_ip_blocked("192.168.1.200") is True
    api_security_service.unblock_ip("192.168.1.200")


# ─── Integration Tests: Identity Governance Service ──────────────────────────


async def test_identity_governance_role_lifecycle(db: AsyncSession):
    """Test role creations, user assignments, and revocations."""
    # Seed a user first
    user = User(
        email="testgovuser@forestfire.org",
        username="gov_user",
        hashed_password=password_service.hash_password("Password123!"),
        is_active=True
    )
    db.add(user)
    await db.flush()

    # Create role
    role_name = "GIS Analyst Lead"
    role = await identity_governance_service.create_role(db, name=role_name, description="Lead GIS Specialist")
    assert role.name == role_name

    # Assign role
    user = await identity_governance_service.assign_role_to_user(db, user_id=user.id, role_name=role_name)
    assert role_name in [r.name for r in user.roles]

    # Revoke role
    user = await identity_governance_service.revoke_role_from_user(db, user_id=user.id, role_name=role_name)
    assert role_name not in [r.name for r in user.roles]


# ─── Integration Tests: Access Reviews Campaigns ─────────────────────────────


async def test_access_review_campaigns_and_revocations(db: AsyncSession):
    """Test creating Campaigns, certifying assignments, and revoking roles on rejection."""
    # Seed reviewer, user, and role
    reviewer = await create_user_with_role(db, "campaign_reviewer", "Super Admin")
    user = await create_user_with_role(db, "target_reviewed_user", "Forest Officer")
    
    # Get role object
    q = select(Role).where(Role.name == "Forest Officer")
    res = await db.execute(q)
    role = res.scalar_one()

    # Create Campaign
    campaign = await access_review_manager.create_campaign(
        db, name="Quarterly Forest Officer Access Review", target_role="Forest Officer", current_user_id=reviewer.id
    )
    assert campaign.name == "Quarterly Forest Officer Access Review"
    assert campaign.status == "ACTIVE"

    # Submit REVOKED decision
    decision = await access_review_manager.submit_decision(
        db,
        campaign_id=campaign.id,
        user_id=user.id,
        role_id=role.id,
        reviewer_id=reviewer.id,
        decision_type="REVOKED",
        justification="User reassigned to desk operations"
    )
    assert decision.decision == "REVOKED"

    # Verify role was immediately revoked from user
    q_user = select(User).where(User.id == user.id).options(selectinload(User.roles))
    res_user = await db.execute(q_user)
    user_refreshed = res_user.scalar_one()
    assert "Forest Officer" not in [r.name for r in user_refreshed.roles]

    # Complete campaign
    campaign = await access_review_manager.complete_campaign(db, campaign_id=campaign.id, current_user_id=reviewer.id)
    assert campaign.status == "COMPLETED"


# ─── Integration Tests: Secrets & Audits ──────────────────────────────────────


async def test_secrets_seeding_and_rotation(db: AsyncSession):
    """Test seeding credentials metadata and execution of rotation workflows."""
    await secret_manager.initialize_and_seed_secrets(db)
    await db.commit()

    meta = await secret_manager.get_secret_metadata(db, "EXTERNAL_GIS_API_KEY")
    assert meta is not None
    assert meta.status == "ACTIVE"

    # Trigger rotation
    old_version = meta.version
    rotated = await credential_rotation_service.rotate_secret(db, "EXTERNAL_GIS_API_KEY")
    assert rotated.version == old_version + 1


# ─── Integration Tests: Data Retention & Compliance ──────────────────────────


async def test_data_retention_pruning(db: AsyncSession):
    """Test execution of data purging workflows."""
    result = await retention_manager.run_data_retention_pruning(db)
    assert result["status"] == "SUCCESS"
    assert "security_events" in result["pruned"]


async def test_compliance_manager_checks(db: AsyncSession):
    """Test seeding policies and executing GDPR/SOC2 compliance checks."""
    await compliance_manager.seed_compliance_policies(db)
    await db.commit()

    # Run SOC2 check
    policy = await compliance_manager.run_compliance_check(db, "SOC2")
    assert policy.name == "SOC2"
    assert policy.status in ["COMPLIANT", "NON_COMPLIANT"]


# ─── API Endpoints Verification ───────────────────────────────────────────────


async def test_security_endpoints_require_auth(client: AsyncClient):
    """Test that security endpoints reject unauthenticated clients."""
    endpoints = [
        "/api/v1/security/audit",
        "/api/v1/security/events",
        "/api/v1/security/compliance",
        "/api/v1/security/access-reviews",
        "/api/v1/security/threats",
        "/api/v1/security/governance"
    ]
    for ep in endpoints:
        response = await client.get(ep)
        assert response.status_code == 401


async def test_security_api_endpoints_as_admin(client: AsyncClient, db: AsyncSession):
    """Test that administrators can fetch security audits and dashboard stats."""
    # Seed admin user
    admin = await create_user_with_role(db, "sec_admin_user", "Super Admin")
    await db.commit()

    headers = await get_auth_headers(client, "sec_admin_user")

    # Governance dashboard
    resp = await client.get("/api/v1/security/governance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_risk_score" in data
    assert "compliance_score" in data

    # Threats summary
    resp = await client.get("/api/v1/security/threats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "threats" in data
    assert "blocked_ips_count" in data

    # Compliance list
    resp = await client.get("/api/v1/security/compliance", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Security events
    resp = await client.get("/api/v1/security/events", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_security_threat_block_middleware(client: AsyncClient, db: AsyncSession):
    """Test that requests with malicious SQL Injection signatures are blocked and IPs auto-blocked."""
    api_security_service.unblock_ip("127.0.0.1")
    # Send a request with SQLi pattern in headers/query
    response = await client.get("/api/v1/health?param=union select null")
    assert response.status_code == 400
    assert "Security threat detected" in response.text

    # IP should be blocked now
    assert api_security_service.is_ip_blocked("127.0.0.1") is True
    # Clean up state
    api_security_service.unblock_ip("127.0.0.1")
