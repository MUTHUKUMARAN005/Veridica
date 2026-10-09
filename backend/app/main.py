from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import current_user
from app.config import Settings
from app.db import request_session, session_factory
from app.models import Idea, IdeaVersion, User
from app.schemas import (
    AuthResponse,
    IdeaCreate,
    IdeaDetail,
    IdeaResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password
from app.services import health


class Readiness(BaseModel):
    status: Literal["ready", "unavailable"]
    services: dict[str, Literal["connected", "unavailable"]]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(title="Veridica API", version="0.1.0")
    application.state.settings = settings
    application.state.session_factory = session_factory(settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @application.get("/api/v1/health/live", tags=["Health"])
    def live() -> dict[str, str]:
        return {"status": "ok", "service": "veridica-api"}

    @application.post(
        "/api/v1/auth/register", response_model=AuthResponse, status_code=201, tags=["Auth"]
    )
    def register(
        payload: RegisterRequest, session: Annotated[Session, Depends(request_session)]
    ) -> AuthResponse:
        email = payload.email.strip().lower()
        if session.scalar(select(User).where(User.email == email)):
            raise HTTPException(
                status_code=409, detail="An account with this email already exists."
            )
        user = User(email=email, password_hash=hash_password(payload.password), role="owner")
        session.add(user)
        session.commit()
        session.refresh(user)
        return _auth_response(user, settings)

    @application.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Auth"])
    def login(
        payload: LoginRequest, session: Annotated[Session, Depends(request_session)]
    ) -> AuthResponse:
        user = session.scalar(
            select(User).where(User.email == payload.email.strip().lower())
        )
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        return _auth_response(user, settings)

    @application.get("/api/v1/auth/me", response_model=UserResponse, tags=["Auth"])
    def me(user: Annotated[User, Depends(current_user)]) -> User:
        return user

    @application.post(
        "/api/v1/ideas", response_model=IdeaResponse, status_code=201, tags=["Ideas"]
    )
    def create_idea(
        payload: IdeaCreate,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        idea = Idea(owner_id=user.id, status="Draft", current_version=1)
        idea.versions.append(_version_from_payload(payload, 1))
        session.add(idea)
        session.commit()
        session.refresh(idea)
        return _idea_response(idea, idea.versions[0])

    @application.get("/api/v1/ideas", response_model=list[IdeaResponse], tags=["Ideas"])
    def list_ideas(
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(request_session)],
    ) -> list[IdeaResponse]:
        ideas = session.scalars(
            select(Idea).where(Idea.owner_id == user.id).order_by(Idea.updated_at.desc())
        ).all()
        return [_idea_response(idea, idea.versions[-1]) for idea in ideas]

    @application.get("/api/v1/ideas/{idea_id}", response_model=IdeaDetail, tags=["Ideas"])
    def get_idea(
        idea_id: str,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaDetail:
        idea = session.scalar(select(Idea).where(Idea.id == idea_id, Idea.owner_id == user.id))
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return IdeaDetail(
            **_idea_response(idea, idea.versions[-1]).model_dump(),
            versions=[_idea_response(idea, version) for version in idea.versions],
        )

    @application.post(
        "/api/v1/ideas/{idea_id}/versions",
        response_model=IdeaResponse,
        status_code=201,
        tags=["Ideas"],
    )
    def create_idea_version(
        idea_id: str,
        payload: IdeaCreate,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        idea = session.scalar(
            select(Idea)
            .where(Idea.id == idea_id, Idea.owner_id == user.id)
            .with_for_update()
        )
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        next_version = idea.current_version + 1
        idea.current_version = next_version
        idea.status = "Draft"
        version = _version_from_payload(payload, next_version)
        idea.versions.append(version)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=409, detail="The idea was updated concurrently; retry."
            ) from error
        session.refresh(idea)
        return _idea_response(idea, version)

    @application.get("/api/v1/health/ready", response_model=Readiness, tags=["Health"])
    def ready(response: Response) -> Readiness:
        checks = {
            "postgres": health.check_postgres(settings),
            "redis": health.check_redis(settings),
        }
        available = all(checks.values())
        response.status_code = 200 if available else 503
        return Readiness(
            status="ready" if available else "unavailable",
            services={
                name: "connected" if connected else "unavailable"
                for name, connected in checks.items()
            },
        )

    return application


def _version_from_payload(payload: IdeaCreate, version: int) -> IdeaVersion:
    return IdeaVersion(
        version=version,
        title=payload.title.strip(),
        category=payload.category.strip(),
        problem=payload.problem.strip(),
        solution=payload.solution.strip(),
        audience=payload.audience.strip(),
        features="|".join(feature.strip() for feature in payload.features if feature.strip()),
        constraints=payload.constraints.strip(),
    )


def _idea_response(idea: Idea, version: IdeaVersion) -> IdeaResponse:
    return IdeaResponse(
        id=idea.id,
        title=version.title,
        category=version.category,
        problem=version.problem,
        solution=version.solution,
        audience=version.audience,
        features=[feature for feature in version.features.split("|") if feature],
        constraints=version.constraints,
        version=version.version,
        status=idea.status,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )


def _auth_response(user: User, settings: Settings) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(
            user.id, user.role, settings.jwt_secret, settings.access_token_minutes
        ),
        user=UserResponse.model_validate(user),
    )


app = create_app()