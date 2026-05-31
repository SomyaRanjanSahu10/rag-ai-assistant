"""
Seed Script
===========
Creates a default admin user for development.
Run once after first startup:

    cd backend
    python seed.py

Or with custom credentials:
    SEED_EMAIL=you@example.com SEED_PASSWORD=mypassword python seed.py
"""

import asyncio
import os


# Default seed credentials (override via env vars)
SEED_EMAIL    = "admin@docmind.dev"
SEED_USERNAME = "admin"
SEED_PASSWORD = "admin123"
SEED_NAME     = "Admin User"


async def seed():
    # Import here so DB URL is loaded from .env first
    from database import init_db, AsyncSessionLocal
    from models.user import User
    from utils.security import hash_password
    from sqlalchemy import select

    print("🌱 Running seed script…")

    # Create tables
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == SEED_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✅ User already exists: {SEED_EMAIL}")
            print(f"   Username : {existing.username}")
            print(f"   Password : (unchanged)")
        else:
            user = User(
                email=SEED_EMAIL,
                username=SEED_USERNAME,
                hashed_password=hash_password(SEED_PASSWORD),
                full_name=SEED_NAME,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            print("✅ Seed user created!")

        print("")
        print("─" * 40)
        print("  Login credentials")
        print("─" * 40)
        print(f"  URL      : http://localhost:3000/login")
        print(f"  Email    : {SEED_EMAIL}")
        print(f"  Password : {SEED_PASSWORD}")
        print("─" * 40)
        print("")
        print("💡 Change the password after first login.")
        print("   Override defaults: SEED_EMAIL=x SEED_PASSWORD=y python seed.py")


if __name__ == "__main__":
    asyncio.run(seed())
