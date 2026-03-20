from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
import uuid

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if len(v) < 8: raise ValueError("Min 8 characters")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    is_admin: bool
    created_at: datetime
    model_config = {"from_attributes": True}
