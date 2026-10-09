from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.entities import Idea, IdeaVersion, User  # noqa: E402,F401