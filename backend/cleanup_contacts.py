import os
import sys
import asyncio

# Setup app context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.domain.entities.contact import Contact
from app.domain.entities.organization import Organization

def cleanup_auto_created_contacts():
    db = SessionLocal()
    
    contacts = db.query(Contact).filter(
        Contact.last_name.like("%(Auto-created)%"),
        Contact.is_deleted == False
    ).all()
    
    print(f"Found {len(contacts)} auto-created contacts to clean up.")
    
    public_domains = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", 
        "icloud.com", "me.com", "msn.com", "googlemail.com", "aol.com"
    }
    
    processed = 0
    orgs_created = 0
    
    for contact in contacts:
        # 1. Clean up last name
        contact.last_name = contact.last_name.replace("(Auto-created)", "").strip()
        
        # 2. Try to assign/create an Organization if email exists
        if contact.email and not contact.organization_id:
            import tldextract
            
            domain_raw = contact.email.split('@')[-1].lower() if '@' in contact.email else None
            ext = tldextract.extract(domain_raw) if domain_raw else None
            
            if ext and ext.domain and ext.suffix:
                root_domain = f"{ext.domain}.{ext.suffix}"
                
                if root_domain not in public_domains:
                    # Find matching Organization
                    org = db.query(Organization).filter(
                        Organization.tenant_id == contact.tenant_id,
                        Organization.is_deleted == False,
                        Organization.website.ilike(f"%{root_domain}%")
                    ).first()
                    
                    if not org:
                        # Create one using the root domain
                        pretty_name = ext.domain.replace('-', ' ').title()
                        
                        org = Organization(
                            name=pretty_name,
                            website=root_domain,
                            tenant_id=contact.tenant_id
                        )
                        db.add(org)
                        db.flush()
                        orgs_created += 1
                        print(f"[{root_domain}] Created Organization: {pretty_name}")
                    
                    contact.organization_id = org.id
                    
        processed += 1
        
    db.commit()
    db.close()
    
    print(f"Cleanup complete. Processed {processed} contacts, created {orgs_created} new organizations.")

if __name__ == "__main__":
    cleanup_auto_created_contacts()
