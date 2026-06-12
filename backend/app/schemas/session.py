import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    device_type: str | None
    is_active: bool
    last_activity_at: datetime
    created_at: datetime
    expires_at: datetime
