import os
import sys

from app.config import settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.seed import seed_admin_user

def reset_admin():
    from main import app
    
    db = SessionLocal()
    from app.infrastructure.persistence.user_repository import UserRepository
    from app.domain.entities.user import User
    repo = UserRepository(db)
    email = settings.admin_email.lower()
    admin = repo.get_by_email(email)
    
    password = "Admin123!"
    hashed = User.hash_password(password)
    
    if admin:
        admin.password_hash = hashed
        repo.update(admin)
        print(f"Updated password for {email}")    
    db.commit()

if __name__ == "__main__":
    reset_admin()
