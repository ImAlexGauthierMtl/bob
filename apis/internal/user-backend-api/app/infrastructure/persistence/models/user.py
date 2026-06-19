"""User entity for auth."""
from sqlalchemy import Column, String, Text, Float, Boolean
from sqlalchemy.orm import relationship
import bcrypt
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class User(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    job_title = Column(String(150), nullable=True)
    phone = Column(String(30), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(150), nullable=True)
    timezone = Column(String(50), nullable=True, default="America/Montreal")
    role = Column(String(30), nullable=False, default="member")
    is_super_admin = Column(Boolean, default=False, nullable=False)
    trust_score = Column(Float, nullable=False, default=0.1)
    active_organization_id = Column(String(36), nullable=True)

    @staticmethod
    def hash_password(password: str) -> str:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def verify_password(self, password: str) -> bool:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, self.password_hash.encode("utf-8"))
