from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    status: str
    stage: str | None
    progress: int
    error: str | None
    meeting_id: int | None
