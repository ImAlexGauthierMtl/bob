from main import app
from app.infrastructure.database import SessionLocal
from app.infrastructure.persistence.user_repository import UserRepository
from app.domain.entities.user import User

def create_test_user():
    db = SessionLocal()
    repo = UserRepository(db)
    
    email = "test@thesmartcrew.com"
    password = "password"
    
    existing = repo.get_by_email(email)
    if existing:
        existing.password_hash = User.hash_password(password)
        repo.update(existing)
        print("Updated test user password")
    else:
        new_user = User(
            email=email,
            password_hash=User.hash_password(password),
            first_name="Test",
            last_name="User",
            role="admin",
            created_by="system-seed",
        )
        repo.create(new_user)
        print("Created test user")
        
    db.commit()
    db.close()

if __name__ == "__main__":
    create_test_user()
