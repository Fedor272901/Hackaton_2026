from pydantic import BaseModel
from typing import List, Optional

class DistrictBase(BaseModel):
    name: str
    description: Optional[str] = None

class DistrictCreate(DistrictBase):
    pass

class DistrictUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class District(DistrictBase):
    id: int

    class Config:
        from_attributes = True  # позволяет конвертировать объект SQLAlchemy в Pydantic

# Краткая схема депутата для вложения
class DeputyShort(BaseModel):
    id: int
    user_id: int
    office_phone: Optional[str] = None
    office_address: Optional[str] = None

    class Config:
        from_attributes = True

# Округ с полным списком депутатов
class DistrictWithDeputies(District):
    deputies: List[DeputyShort] = []