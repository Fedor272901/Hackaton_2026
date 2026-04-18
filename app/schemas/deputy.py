from pydantic import BaseModel
from typing import Optional

class DeputyBase(BaseModel):
    user_id: int
    district_id: int
    office_phone: Optional[str] = None
    office_address: Optional[str] = None

class DeputyCreate(DeputyBase):
    pass

class DeputyUpdate(BaseModel):
    user_id: Optional[int] = None
    district_id: Optional[int] = None
    office_phone: Optional[str] = None
    office_address: Optional[str] = None

class Deputy(DeputyBase):
    id: int

    class Config:
        from_attributes = True