"""All CRM schemas — Pydantic models."""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime, date

# ── Organization ──────────────────────────────
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = None; website: Optional[str] = None; phone: Optional[str] = None; email: Optional[str] = None
    address_street: Optional[str] = None; address_city: Optional[str] = None; address_state: Optional[str] = None
    address_country: Optional[str] = None; address_postal_code: Optional[str] = None
    status: Optional[str] = "PROSPECT"; org_type: Optional[str] = "OTHER"
    employee_count: Optional[int] = None; annual_revenue: Optional[float] = None
    description: Optional[str] = None; linkedin_url: Optional[str] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = None; website: Optional[str] = None; phone: Optional[str] = None; email: Optional[str] = None
    address_street: Optional[str] = None; address_city: Optional[str] = None; address_state: Optional[str] = None
    address_country: Optional[str] = None; address_postal_code: Optional[str] = None
    status: Optional[str] = None; org_type: Optional[str] = None
    employee_count: Optional[int] = None; annual_revenue: Optional[float] = None
    description: Optional[str] = None; linkedin_url: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: str; name: str; industry: Optional[str] = None; website: Optional[str] = None
    phone: Optional[str] = None; email: Optional[str] = None
    address_street: Optional[str] = None; address_city: Optional[str] = None
    address_state: Optional[str] = None; address_country: Optional[str] = None; address_postal_code: Optional[str] = None
    status: Optional[str] = None; org_type: Optional[str] = None
    employee_count: Optional[int] = None; annual_revenue: Optional[float] = None; description: Optional[str] = None
    ai_enriched: Optional[str] = None; linkedin_url: Optional[str] = None; logo_url: Optional[str] = None
    organization_profile: Optional[Dict[str, Any]] = None
    created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

class OrganizationListResponse(BaseModel):
    items: List[OrganizationResponse]; total: int; skip: int; limit: int

# ── Contact ──────────────────────────────
class ContactCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100); last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None; phone: Optional[str] = None; mobile: Optional[str] = None
    job_title: Optional[str] = None; department: Optional[str] = None
    status: Optional[str] = "ACTIVE"; linkedin_url: Optional[str] = None; notes: Optional[str] = None
    organization_id: Optional[str] = None

class ContactUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100); last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None; phone: Optional[str] = None; mobile: Optional[str] = None
    job_title: Optional[str] = None; department: Optional[str] = None; status: Optional[str] = None
    linkedin_url: Optional[str] = None; notes: Optional[str] = None; organization_id: Optional[str] = None

class ContactResponse(BaseModel):
    id: str; first_name: str; last_name: str; email: Optional[str] = None
    phone: Optional[str] = None; mobile: Optional[str] = None; job_title: Optional[str] = None
    department: Optional[str] = None; seniority: Optional[str] = None; status: Optional[str] = None
    linkedin_url: Optional[str] = None; headline: Optional[str] = None; profile_picture_url: Optional[str] = None
    notes: Optional[str] = None; contact_profile: Optional[dict] = None; linkedin_followers: Optional[list] = None
    organization_id: Optional[str] = None; created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

class ContactListResponse(BaseModel):
    items: List[ContactResponse]; total: int; skip: int; limit: int

# ── Opportunity ──────────────────────────────
class OpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255); description: Optional[str] = None
    stage: Optional[str] = "PROSPECTING"; priority: Optional[str] = "MEDIUM"
    amount: Optional[float] = None; probability: Optional[float] = None; close_date: Optional[date] = None
    source: Optional[str] = None; organization_id: Optional[str] = None; contact_id: Optional[str] = None

class OpportunityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255); description: Optional[str] = None
    stage: Optional[str] = None; priority: Optional[str] = None
    amount: Optional[float] = None; probability: Optional[float] = None; close_date: Optional[date] = None
    source: Optional[str] = None; organization_id: Optional[str] = None; contact_id: Optional[str] = None

class OpportunityResponse(BaseModel):
    id: str; name: str; description: Optional[str] = None; stage: Optional[str] = None
    priority: Optional[str] = None; amount: Optional[float] = None; probability: Optional[float] = None
    close_date: Optional[date] = None; source: Optional[str] = None
    organization_id: Optional[str] = None; contact_id: Optional[str] = None
    created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

class OpportunityListResponse(BaseModel):
    items: List[OpportunityResponse]; total: int; skip: int; limit: int

# ── Quote ──────────────────────────────
class QuoteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255); description: Optional[str] = None
    status: Optional[str] = "DRAFT"; subtotal: Optional[float] = 0.0
    discount_percent: Optional[float] = 0.0; tax_percent: Optional[float] = 0.0; total: Optional[float] = 0.0
    valid_until: Optional[date] = None; terms: Optional[str] = None; notes: Optional[str] = None
    opportunity_id: Optional[str] = None; organization_id: Optional[str] = None

class QuoteUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None; status: Optional[str] = None
    subtotal: Optional[float] = None; discount_percent: Optional[float] = None
    tax_percent: Optional[float] = None; total: Optional[float] = None
    valid_until: Optional[date] = None; terms: Optional[str] = None; notes: Optional[str] = None

class QuoteResponse(BaseModel):
    id: str; name: str; description: Optional[str] = None; status: Optional[str] = None
    subtotal: Optional[float] = None; discount_percent: Optional[float] = None
    tax_percent: Optional[float] = None; total: Optional[float] = None
    valid_until: Optional[date] = None; terms: Optional[str] = None; notes: Optional[str] = None
    opportunity_id: Optional[str] = None; organization_id: Optional[str] = None
    created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

class QuoteListResponse(BaseModel):
    items: List[QuoteResponse]; total: int; skip: int; limit: int

# ── Activity ──────────────────────────────
class ActivityCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255); description: Optional[str] = None
    activity_type: Optional[str] = "TASK"; priority: Optional[str] = "MEDIUM"; status: Optional[str] = "PENDING"
    due_date: Optional[datetime] = None
    organization_ids: Optional[List[str]] = []; contact_ids: Optional[List[str]] = []; opportunity_ids: Optional[List[str]] = []
    assigned_to: Optional[str] = None; owner_id: Optional[str] = None

class ActivityUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=255); description: Optional[str] = None
    activity_type: Optional[str] = None; priority: Optional[str] = None; status: Optional[str] = None
    due_date: Optional[datetime] = None; completed_at: Optional[datetime] = None
    organization_ids: Optional[List[str]] = None; contact_ids: Optional[List[str]] = None; opportunity_ids: Optional[List[str]] = None
    assigned_to: Optional[str] = None; owner_id: Optional[str] = None

class ActivityResponse(BaseModel):
    id: str; subject: str; description: Optional[str] = None; activity_type: Optional[str] = None
    priority: Optional[str] = None; status: Optional[str] = None
    due_date: Optional[datetime] = None; completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None; owner_id: Optional[str] = None
    created_at: datetime; updated_at: datetime
    organization_ids: Optional[List[str]] = []; contact_ids: Optional[List[str]] = []; opportunity_ids: Optional[List[str]] = []
    class Config: from_attributes = True

class ActivityListResponse(BaseModel):
    items: List[ActivityResponse]; total: int; skip: int; limit: int

# ── Product ──────────────────────────────
class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200); description: Optional[str] = None
    category: str = "SOFTWARE"; unit_price: float = 0; currency: str = "CAD"
    sku: Optional[str] = None; is_taxable: bool = True; tax_rate: Optional[float] = None
    billing_cycle: Optional[str] = None; contract_term_months: Optional[int] = None; setup_fee: Optional[float] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None; category: Optional[str] = None
    unit_price: Optional[float] = None; currency: Optional[str] = None; sku: Optional[str] = None
    is_active: Optional[bool] = None; is_taxable: Optional[bool] = None; tax_rate: Optional[float] = None

class ProductResponse(BaseModel):
    id: str; name: str; description: Optional[str] = None; category: Optional[str] = None
    unit_price: float; currency: str; sku: Optional[str] = None
    is_active: bool; is_taxable: bool; tax_rate: Optional[float] = None
    created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

class ProductListResponse(BaseModel):
    items: List[ProductResponse]; total: int; skip: int; limit: int

# ── Department ──────────────────────────────
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150); description: Optional[str] = None; manager_user_id: Optional[str] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None; manager_user_id: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: str; name: str; description: Optional[str] = None; manager_user_id: Optional[str] = None
    created_at: datetime; updated_at: datetime
    class Config: from_attributes = True

# ── OpportunityProduct line items ──────────────────────────────
class OpportunityProductCreate(BaseModel):
    product_id: str; quantity: int = 1; unit_price: float; discount_percent: Optional[float] = None; notes: Optional[str] = None

class OpportunityProductResponse(BaseModel):
    id: str; opportunity_id: str; product_id: str; quantity: int; unit_price: float
    discount_percent: Optional[float] = None; notes: Optional[str] = None
    class Config: from_attributes = True
