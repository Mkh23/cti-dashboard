from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True

class MeOut(BaseModel):
    id: int
    email: EmailStr
    roles: list[str]
