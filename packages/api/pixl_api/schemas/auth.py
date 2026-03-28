"""Pydantic request/response models for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: str


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    workspace_id: str


class TokenResponse(BaseModel):
    token: str
