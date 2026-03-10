from main import app
from app.infrastructure.database import SessionLocal
from app.domain.entities.organization import Organization, OrganizationStatus, OrganizationType
from app.domain.entities.contact import Contact
import uuid

def seed_crm():
    db = SessionLocal()
    tenant_id = "default"  # Using default tenant which is what admin gets by default
    
    # Check if orgs already exist
    existing = db.query(Organization).filter_by(tenant_id=tenant_id).count()
    if existing > 0:
        print(f"Entities already exist: {existing} orgs found.")
        return
        
    org1 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Tech Innovators Inc",
        industry="Technology",
        website="https://techinnovators.example.com",
        phone="555-0101",
        email="hello@techinnovators.example.com",
        address_city="Montreal",
        address_country="Canada",
        status=OrganizationStatus.CUSTOMER,
        org_type=OrganizationType.CORPORATION,
        description="A leading technology firm."
    )
    
    org2 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Global Logistics Corp",
        industry="Logistics",
        website="https://globallogistics.example.com",
        phone="555-0202",
        email="contact@globallogistics.example.com",
        address_city="Toronto",
        address_country="Canada",
        status=OrganizationStatus.PROSPECT,
        org_type=OrganizationType.CORPORATION,
        description="International shipping and logistics provider."
    )
    
    db.add(org1)
    db.add(org2)
    db.flush()
    
    contact1 = Contact(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        organization_id=org1.id,
        first_name="Alice",
        last_name="Smith",
        email="alice.smith@techinnovators.example.com",
        job_title="CTO",
        phone="555-1111",
    )
    
    contact2 = Contact(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        organization_id=org2.id,
        first_name="Bob",
        last_name="Johnson",
        email="bob.j@globallogistics.example.com",
        job_title="VP Operations",
        phone="555-2222",
    )
    
    db.add(contact1)
    db.add(contact2)
    
    db.commit()
    print("Successfully seeded 2 organizations and 2 contacts.")
    db.close()

if __name__ == "__main__":
    seed_crm()
