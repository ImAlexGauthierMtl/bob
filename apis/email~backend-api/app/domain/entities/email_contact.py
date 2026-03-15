"""Email ↔ Contact junction table — Many-to-Many linking.

Each email can be linked to multiple contacts with a role (from, to, cc).
This replaces the single linked_contact_id FK for comprehensive CRM linking.
"""

from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from shared.database import Base, generate_uuid


# Junction table: synced_emails ↔ contacts
email_contacts = Table(
    "email_contacts",
    Base.metadata,
    Column("id", String(36), primary_key=True, default=generate_uuid),
    Column("synced_email_id", String(36), ForeignKey("synced_emails.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("contact_id", String(36), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("role", String(10), nullable=False, default="from", comment="from | to | cc"),
)
