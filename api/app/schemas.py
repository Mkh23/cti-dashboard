from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

class RegistrationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str
    address: str
    requested_role: Literal["farmer", "technician"]

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    registration_status: RegistrationStatus
    class Config:
        from_attributes = True

class MeOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    roles: list[str]
    registration_status: RegistrationStatus

class UpdateProfile(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
