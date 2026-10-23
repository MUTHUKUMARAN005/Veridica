from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.main import create_app

settings = Settings()
application = create_app(settings)
application.state.session_factory.kw["bind"].dispose()

engine = create_engine(str(settings.database_url), pool_pre_ping=True)
connection = engine.connect()
transaction = connection.begin()
application.state.session_factory = sessionmaker(
    bind=connection,
    autoflush=False,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
)


def rollback_test_data() -> None:
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    engine.dispose()


application.router.on_shutdown.append(rollback_test_data)
app: FastAPI = application
