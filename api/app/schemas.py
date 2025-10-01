from pydantic import BaseModel, EmailStr
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    class Config:
        from_attributes = True

class MeOut(BaseModel):
    id: UUID
    email: EmailStr
    roles: list[str]
