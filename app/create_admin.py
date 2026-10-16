
import getpass

import bcrypt
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User


def create_admin():
    db: Session = SessionLocal()

    try:
        name = input("Enter admin name: ").strip()
        email = input("Enter admin email: ").strip().lower()
        password = getpass.getpass("Enter admin password: ")

        if not name or not email or not password:
            print("Name, email and password are required.")
            return

        if len(password) < 8:
            print("Password must contain at least 8 characters.")
            return

        existing_user = db.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            print("An account with this email already exists.")
            print("No changes were made.")
            return

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        admin = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            role="admin",
        )

        db.add(admin)
        db.commit()

        print("Admin account created successfully.")

    except Exception:
        db.rollback()
        print("Admin creation failed. Check your database setup.")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
