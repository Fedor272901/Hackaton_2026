<<<<<<< HEAD
from pydantic import BaseModel
from typing import List, Optional
=======
<<<<<<< HEAD
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.deputy import DeputyResponse

=======
from pydantic import BaseModel
from typing import List, Optional
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

class DistrictBase(BaseModel):
    name: str
    description: Optional[str] = None
<<<<<<< HEAD
=======
<<<<<<< HEAD
    geometry: Optional[str] = None

=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

class DistrictCreate(DistrictBase):
    pass

<<<<<<< HEAD
=======
<<<<<<< HEAD

class DistrictUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    geometry: Optional[str] = None


class DistrictResponse(DistrictBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DistrictWithDeputies(DistrictResponse):
    deputies: List["DeputyResponse"] = []
=======
>>>>>>> front/dev
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
<<<<<<< HEAD
    deputies: List[DeputyShort] = []
=======
    deputies: List[DeputyShort] = []
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
