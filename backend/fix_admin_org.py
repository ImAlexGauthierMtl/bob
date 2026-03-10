from main import app
from app.infrastructure.database import SessionLocal
from app.domain.entities.user import User
from app.domain.entities.bcc_entities import BccOrganization

def fix_admin_org():
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@croo.digital").first()
    if admin:
        org = db.query(BccOrganization).first()
        if org:
            admin.active_organization_id = org.id
            db.commit()
            print(f"Set active_organization_id for admin to {org.name}")
        else:
            print("No organizations found to link!")
    else:
        print("Admin user not found")
    db.close()

if __name__ == "__main__":
    fix_admin_org()
