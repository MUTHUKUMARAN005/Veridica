from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def session_factory(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(
        bind=create_engine(str(settings.database_url), pool_pre_ping=True),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session(settings: Settings) -> Generator[Session, None, None]:
    factory = session_factory(settings)
    with factory() as session:
        yield session


def request_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session
