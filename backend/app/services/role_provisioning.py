from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import RoleChangeEvent, User

ROLES = {"owner", "reviewer", "admin"}
ADVISORY_LOCK_ID = 1_447_387_721


class RoleProvisioningError(ValueError):
    pass


def provision_user_role(
    session: Session,
    *,
    target_email: str,
    new_role: str,
    reason: str,
    actor_email: str | None = None,
    bootstrap_admin: bool = False,
) -> RoleChangeEvent:
    target_email = target_email.strip().lower()
    normalized_reason = reason.strip()
    normalized_actor = actor_email.strip().lower() if actor_email else None
    if new_role not in ROLES:
        raise RoleProvisioningError("Role must be owner, reviewer, or admin.")
    if not normalized_reason or len(normalized_reason) > 1000:
        raise RoleProvisioningError("Provide a reason between 1 and 1000 characters.")
    if not target_email:
        raise RoleProvisioningError("Target email is required.")

    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID},
        )

    target = session.scalar(
        select(User).where(func.lower(User.email) == target_email).with_for_update()
    )
    if target is None:
        raise RoleProvisioningError(
            "Target account does not exist; register it before provisioning."
        )
    if target.role == new_role:
        raise RoleProvisioningError("The account already has the requested role.")

    admin_count = (
        session.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0
    )
    if bootstrap_admin:
        if new_role != "admin":
            raise RoleProvisioningError("Bootstrap can only grant the admin role.")
        if admin_count:
            raise RoleProvisioningError("Bootstrap is allowed only when no admin account exists.")
        if normalized_actor not in {None, target_email}:
            raise RoleProvisioningError("Bootstrap actor must be the account being promoted.")
        actor = target
    else:
        if normalized_actor is None:
            raise RoleProvisioningError("An existing admin actor email is required.")
        actor = session.scalar(
            select(User).where(func.lower(User.email) == normalized_actor).with_for_update()
        )
        if actor is None or actor.role != "admin":
            raise RoleProvisioningError("Only an existing admin account may change roles.")
        if target.role == "admin" and new_role != "admin" and admin_count <= 1:
            raise RoleProvisioningError("The final admin account cannot be demoted.")

    previous_role = target.role
    target.role = new_role
    event = RoleChangeEvent(
        target_user_id=target.id,
        actor_user_id=actor.id,
        previous_role=previous_role,
        new_role=new_role,
        reason=normalized_reason,
    )
    session.add(event)
    return event
