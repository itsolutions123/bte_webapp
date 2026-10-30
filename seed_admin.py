"""One-off script to seed the first admin user. Run interactively: docker exec -it bte_careers_web python3 seed_admin.py
Password is entered via getpass (hidden, not echoed, never logged) and hashed with the same
passlib/bcrypt context used by app/routers/auth.py before it touches the DB.
"""
import asyncio
import getpass
import sys

from passlib.context import CryptContext
from sqlalchemy import select

from app.database import async_session
from app.models import User

VALID_ROLES = {"SUPERADMIN", "MANAGER", "RECRUITER"}
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def main():
    email = input("Email: ").strip().lower()
    if not email or "@" not in email:
        sys.exit("Not a valid-looking email. Aborting.")

    role = input(f"Role ({'/'.join(sorted(VALID_ROLES))}): ").strip().upper()
    if role not in VALID_ROLES:
        sys.exit(f"Role must be one of {sorted(VALID_ROLES)}. Aborting.")

    password = getpass.getpass("Password (hidden): ")
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        sys.exit("Passwords did not match. Aborting.")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters. Aborting.")

    password_hash = pwd_context.hash(password)

    async with async_session() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is not None:
            sys.exit(f"A user with email {email} already exists. Aborting (this script only creates new users).")

        db.add(User(email=email, password_hash=password_hash, role=role))
        await db.commit()

    print(f"Created {role} user: {email}")

if __name__ == "__main__":
    asyncio.run(main())
