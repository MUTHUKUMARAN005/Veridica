import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.models import Base, RoleChangeEvent, User
from app.services.role_provisioning import RoleProvisioningError, provision_user_role


@pytest.fixture
def role_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def add_user(session, email: str, role: str = "owner") -> User:
    user = User(email=email, password_hash="test-hash", role=role)
    session.add(user)
    session.flush()
    return user


def test_bootstrap_admin_and_audited_admin_role_change(role_session):
    bootstrap = add_user(role_session, "admin@example.invalid")
    event = provision_user_role(
        role_session,
        target_email=bootstrap.email,
        new_role="admin",
        reason="Initial local operator setup",
        bootstrap_admin=True,
    )
    role_session.commit()
    assert bootstrap.role == "admin"
    assert event.actor_user_id == bootstrap.id
    assert event.previous_role == "owner"
    assert event.new_role == "admin"

    reviewer = add_user(role_session, "reviewer@example.invalid")
    event = provision_user_role(
        role_session,
        target_email=reviewer.email,
        new_role="reviewer",
        actor_email=bootstrap.email,
        reason="Reviewer account approved by the project operator",
    )
    role_session.commit()
    assert reviewer.role == "reviewer"
    assert event.actor_user_id == bootstrap.id
    assert event.target_user_id == reviewer.id
    assert event.reason == "Reviewer account approved by the project operator"
    assert role_session.scalar(select(RoleChangeEvent).where(RoleChangeEvent.id == event.id))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"actor_email": "owner@example.invalid"}, "Only an existing admin"),
        ({"actor_email": None}, "admin actor email is required"),
        ({"bootstrap_admin": True, "new_role": "admin"}, "only when no admin"),
    ],
)
def test_rejects_unauthorized_or_repeated_bootstrap(role_session, overrides, message):
    target = add_user(role_session, "target@example.invalid")
    add_user(role_session, "admin@example.invalid", "admin")
    params = {
        "target_email": target.email,
        "new_role": "reviewer",
        "reason": "approved",
        "actor_email": "admin@example.invalid",
        "bootstrap_admin": False,
    }
    params.update(overrides)
    with pytest.raises(RoleProvisioningError, match=message):
        provision_user_role(role_session, **params)
    role_session.rollback()
    assert target.role == "owner"
    assert role_session.scalar(select(RoleChangeEvent)) is None


def test_last_admin_cannot_be_demoted(role_session):
    admin = add_user(role_session, "admin@example.invalid", "admin")
    with pytest.raises(RoleProvisioningError, match="final admin"):
        provision_user_role(
            role_session,
            target_email=admin.email,
            new_role="owner",
            actor_email=admin.email,
            reason="Attempted demotion",
        )
    role_session.rollback()
    assert admin.role == "admin"
    assert role_session.scalar(select(RoleChangeEvent)) is None


def test_requires_existing_target_nonempty_reason_and_real_role(role_session):
    add_user(role_session, "admin@example.invalid", "admin")
    role_session.commit()
    for arguments, message in [
        (
            {
                "target_email": "missing@example.invalid",
                "new_role": "reviewer",
                "reason": "approved",
                "actor_email": "admin@example.invalid",
            },
            "Target account does not exist",
        ),
        (
            {
                "target_email": "admin@example.invalid",
                "new_role": "admin",
                "reason": "no change",
                "actor_email": "admin@example.invalid",
            },
            "already has the requested role",
        ),
        (
            {
                "target_email": "admin@example.invalid",
                "new_role": "administer",
                "reason": "invalid role",
                "actor_email": "admin@example.invalid",
            },
            "Role must be owner",
        ),
        (
            {
                "target_email": "admin@example.invalid",
                "new_role": "reviewer",
                "reason": " ",
                "actor_email": "admin@example.invalid",
            },
            "Provide a reason",
        ),
    ]:
        with pytest.raises(RoleProvisioningError, match=message):
            provision_user_role(role_session, **arguments)
        role_session.rollback()


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires PostgreSQL")
def test_postgres_role_audit_trigger_is_append_only():
    engine = create_engine(str(Settings().database_url), poolclass=StaticPool)
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    suffix = uuid4().hex
    try:
        with factory() as session:
            admin = add_user(session, f"role-admin-{suffix}@example.invalid", "admin")
            owner = add_user(session, f"role-owner-{suffix}@example.invalid")
            event = provision_user_role(
                session,
                target_email=owner.email,
                new_role="reviewer",
                actor_email=admin.email,
                reason="PostgreSQL immutable audit integration test",
            )
            session.commit()
            with pytest.raises(DBAPIError, match="append-only"):
                session.execute(
                    update(RoleChangeEvent)
                    .where(RoleChangeEvent.id == event.id)
                    .values(reason="tampered")
                )
            session.rollback()
            with pytest.raises(DBAPIError, match="append-only"):
                session.execute(
                    delete(RoleChangeEvent).where(RoleChangeEvent.id == event.id)
                )
            session.rollback()
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()
