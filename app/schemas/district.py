from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.deputy import DeputyResponse


class DistrictBase(BaseModel):
    name: str
    description: Optional[str] = None
    geometry: Optional[str] = None


class DistrictCreate(DistrictBase):
    pass


class DistrictUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    geometry: Optional[str] = None


class DistrictResponse(DistrictBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DistrictWithDeputies(DistrictResponse):
    deputies: List["DeputyResponse"] = []