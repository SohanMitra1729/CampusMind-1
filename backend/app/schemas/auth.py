"""
app/schemas/auth.py — Authentication Request/Response Schemas
"""

from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    username: str
    scholar_id: str
    password: str


class LoginRequest(BaseModel):
    identifier: str
    password: str


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    access_token: str
    password: str


class AdminAuthRequest(BaseModel):
    username: str
    password: str
