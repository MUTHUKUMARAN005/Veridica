import argparse
import sys

from app.config import Settings
from app.db import session_factory
from app.services.role_provisioning import RoleProvisioningError, provision_user_role


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision an existing account role with a PostgreSQL audit record."
    )
    parser.add_argument("--email", required=True, help="Existing account to change")
    parser.add_argument("--role", required=True, choices=("owner", "reviewer", "admin"))
    parser.add_argument("--reason", required=True, help="Operational reason for the role change")
    parser.add_argument(
        "--actor-email",
        help="Existing admin account authorizing the change (required except bootstrap)",
    )
    parser.add_argument(
        "--bootstrap-admin",
        action="store_true",
        help="One-time bootstrap when no admin exists; actor is the account being promoted",
    )
    args = parser.parse_args()

    factory = session_factory(Settings())
    try:
        with factory() as session:
            event = provision_user_role(
                session,
                target_email=args.email,
                new_role=args.role,
                reason=args.reason,
                actor_email=args.actor_email,
                bootstrap_admin=args.bootstrap_admin,
            )
            session.commit()
            print(
                f"Role changed: {args.email.strip().lower()} "
                f"{event.previous_role} -> {event.new_role}; audit event {event.id}"
            )
    except RoleProvisioningError as error:
        print(f"Role provisioning rejected: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
