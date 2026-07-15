from pydantic import BaseModel, EmailStr
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str

    class Config:
        from_attributes = True   # lets Pydantic read directly from SQLAlchemy objects

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"