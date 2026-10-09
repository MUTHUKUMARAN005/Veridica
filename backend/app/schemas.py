from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(RegisterRequest):
    pass


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class IdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    problem: str = Field(min_length=10, max_length=10_000)
    solution: str = Field(min_length=10, max_length=10_000)
    audience: str = Field(min_length=2, max_length=5_000)
    features: list[str] = Field(min_length=1, max_length=30)
    constraints: str = Field(default="", max_length=5_000)

    @field_validator(
        "title", "category", "problem", "solution", "audience", "constraints", mode="before"
    )
    @classmethod
    def trim_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("features", mode="before")
    @classmethod
    def normalize_features(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            return value
        normalized = [
            feature.strip()
            for feature in value
            if isinstance(feature, str) and feature.strip()
        ]
        if not normalized:
            raise ValueError("At least one non-empty feature is required.")
        return normalized


class IdeaResponse(IdeaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime


class IdeaDetail(IdeaResponse):
    versions: list[IdeaResponse]
