from pydantic import BaseModel


class StatusCreate(BaseModel):
    code: str
    name: str


class StatusUpdate(BaseModel):
    code: str | None = None
    name: str | None = None


class StatusRead(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True
