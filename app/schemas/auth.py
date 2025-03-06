from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=20, description="Username must be between 3-30 characters.")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long.")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

