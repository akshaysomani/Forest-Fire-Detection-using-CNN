import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, Uuid, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel


class AccessReviewCampaign(BaseModel):
    __tablename__ = "access_review_campaigns"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessReviewDecision(BaseModel):
    __tablename__ = "access_review_decisions"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("access_review_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # 'CERTIFIED', 'REVOKED'
    decision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    justification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class SecretMetadata(BaseModel):
    __tablename__ = "secret_metadata"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    encryption_algorithm: Mapped[str] = mapped_column(String(50), default="Fernet", nullable=False)
    last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    next_rotation_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_interval_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)


class SecretRotationLog(BaseModel):
    __tablename__ = "secret_rotation_logs"

    secret_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    rotated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'SUCCESS', 'FAILURE'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SecurityEvent(BaseModel):
    __tablename__ = "security_events"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'INFO', 'WARNING', 'HIGH', 'CRITICAL'
    description: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class CompliancePolicy(BaseModel):
    __tablename__ = "compliance_policies"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'GDPR', 'HIPAA', 'SOC2', 'INTERNAL'
    status: Mapped[str] = mapped_column(String(50), default="COMPLIANT", nullable=False, index=True)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ComplianceAudit(BaseModel):
    __tablename__ = "compliance_audits"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    checked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'PASS', 'FAIL'
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class DataRetentionLog(BaseModel):
    __tablename__ = "data_retention_logs"

    execution_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    records_pruned: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'SUCCESS', 'FAILURE'
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
