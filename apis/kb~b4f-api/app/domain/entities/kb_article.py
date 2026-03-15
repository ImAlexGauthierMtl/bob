"""Knowledge Base entities — Category and Article."""

import enum
from sqlalchemy import Column, String, Text, Integer, Boolean, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class ArticleVisibility(str, enum.Enum):
    """Controls who can see the article."""
    INTERNAL = "internal"   # Tenant maître only (The Smart Crew)
    SHARED = "shared"       # Us + clients with the module
    PUBLIC = "public"       # Everyone (unauthenticated OK)


class KBCategory(Base, TenantMixin, AuditMixin):
    """Knowledge Base category."""

    __tablename__ = "kb_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)       # FontAwesome class
    color = Column(String(50), nullable=True)        # Hex or CSS color
    sort_order = Column(Integer, default=0)
    article_count = Column(Integer, default=0)

    articles = relationship("KBArticle", back_populates="category", lazy="dynamic")


class KBArticle(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Knowledge Base article."""

    __tablename__ = "kb_articles"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Content
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, index=True, unique=True)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=False, default="")

    # Classification
    category_id = Column(String(36), ForeignKey("kb_categories.id"), nullable=True, index=True)
    category = relationship("KBCategory", back_populates="articles")
    tags = Column(JSON, nullable=True, default=list)

    # Visibility & access
    visibility = Column(SAEnum(ArticleVisibility), default=ArticleVisibility.SHARED, nullable=False, index=True)
    required_module = Column(String(100), nullable=True)   # contacts, automation, ai, etc.
    required_role = Column(String(50), nullable=True)       # admin, manager, or null = any

    # Author info
    author_name = Column(String(200), nullable=True)
    author_role = Column(String(200), nullable=True)
    author_avatar = Column(String(500), nullable=True)

    # Metrics
    read_time_minutes = Column(Integer, default=5)
    view_count = Column(Integer, default=0)
    helpful_yes = Column(Integer, default=0)
    helpful_no = Column(Integer, default=0)

    # Publishing
    is_published = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False)
