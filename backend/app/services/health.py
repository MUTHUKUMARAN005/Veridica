import logging

from redis import Redis
from sqlalchemy import create_engine, text

from app.config import Settings

logger = logging.getLogger(__name__)


def check_postgres(settings: Settings) -> bool:
    engine = create_engine(str(settings.database_url), connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as connection:
            extension = connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            return bool(extension and revision)
    except Exception:
        logger.warning("PostgreSQL readiness check failed")
        return False
    finally:
        engine.dispose()


def check_redis(settings: Settings) -> bool:
    try:
        with Redis.from_url(
            str(settings.redis_url), socket_connect_timeout=2, socket_timeout=2
        ) as client:
            return bool(client.ping())
    except Exception:
        logger.warning("Redis readiness check failed")
        return False