from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class DeputyBase(BaseModel):
    user_id: int
    district_id: int


class DeputyCreate(DeputyBase):
    pass


class DeputyUpdate(BaseModel):
    district_id: Optional[int] = None


class DeputyResponse(DeputyBase):
    id: int
    appointed_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssignDeputyRequest(BaseModel):
    user_id: int
    district_id: int