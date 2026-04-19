<<<<<<< HEAD
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

=======
from pydantic import BaseModel
from typing import Optional
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

class DeputyBase(BaseModel):
    user_id: int
    district_id: int
<<<<<<< HEAD

=======
    office_phone: Optional[str] = None
    office_address: Optional[str] = None
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

class DeputyCreate(DeputyBase):
    pass

<<<<<<< HEAD

class DeputyUpdate(BaseModel):
    district_id: Optional[int] = None


class DeputyResponse(DeputyBase):
    id: int
    appointed_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssignDeputyRequest(BaseModel):
    user_id: int
    district_id: int
=======
class DeputyUpdate(BaseModel):
    user_id: Optional[int] = None
    district_id: Optional[int] = None
    office_phone: Optional[str] = None
    office_address: Optional[str] = None

class Deputy(DeputyBase):
    id: int

    class Config:
        from_attributes = True
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
