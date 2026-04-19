# app/schemas/district.py

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from app.schemas.deputy import DeputyResponse


class GeoJSONPolygon(BaseModel):
    """GeoJSON для Polygon"""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]
    
    @field_validator('type')
    def validate_type(cls, v):
        if v != "Polygon":
            raise ValueError('type must be "Polygon"')
        return v


class GeoJSONMultiPolygon(BaseModel):
    """GeoJSON для MultiPolygon"""
    type: str = "MultiPolygon"
    coordinates: List[List[List[List[float]]]]
    
    @field_validator('type')
    def validate_type(cls, v):
        if v != "MultiPolygon":
            raise ValueError('type must be "MultiPolygon"')
        return v


class DistrictBase(BaseModel):
    name: str
    description: Optional[str] = None


class DistrictCreate(DistrictBase):
    geometry: Union[GeoJSONPolygon, GeoJSONMultiPolygon]  # Принимает оба типа


class DistrictUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    geometry: Optional[Union[GeoJSONPolygon, GeoJSONMultiPolygon]] = None


class DistrictResponse(DistrictBase):
    id: int
    geometry: Optional[Dict[str, Any]] = None  # GeoJSON для фронта
    model_config = ConfigDict(from_attributes=True)


class DistrictWithDeputies(DistrictResponse):
    deputies: List["DeputyResponse"] = []


class PointCheckRequest(BaseModel):
    latitude: float
    longitude: float


class PointCheckResponse(BaseModel):
    is_inside: bool
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    message: str