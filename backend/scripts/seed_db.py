"""Securely create, verify, or reset the configured first administrator."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path
from pymongo.errors import PyMongoError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.indexes import create_db_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.services.admin_provisioning import (
    create_first_admin,
    reset_admin_password,
    verify_admin_credentials,
    validate_admin_password,
)


def _prompt_new_password() -> str:
    password = getpass.getpass("Administrator password (8-12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    validate_admin_password(password)
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


async def run(action: str, email: str, name: str = "") -> int:
    await connect_to_mongo()
    try:
        await create_db_indexes()
        db = get_database()
        if action == "create":
            password = _prompt_new_password()
            result = await create_first_admin(db, email, name, password)
            print(f"Initial administrator created in database '{db.name}'.")
            return 0 if result == "created" else 1

        if action == "verify":
            password = getpass.getpass("Administrator password: ")
            if await verify_admin_credentials(db, email, password):
                print("Administrator account, role, and password verified.")
                return 0
            print("Administrator account verification failed.")
            return 1

        password = _prompt_new_password()
        await reset_admin_password(db, email, password)
        print("Administrator password reset successfully.")
        return 0
    finally:
        await close_mongo_connection()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify", "reset-password"))
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--name", default="System Administrator", help="Name used only when creating the first admin")
    args = parser.parse_args()

    try:
        return asyncio.run(run(args.action, args.email, args.name))
    except (ValueError, RuntimeError) as exc:
        print(f"Administrator setup failed: {exc}", file=sys.stderr)
        return 1
    except PyMongoError:
        print("Administrator setup failed because of a MongoDB operation error; details were omitted.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
