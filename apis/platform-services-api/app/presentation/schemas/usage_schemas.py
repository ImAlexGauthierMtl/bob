"""Usage API Schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UsageRecordCreate(BaseModel):
    """Create a usage record."""
    resource_type: str
    quantity: int
    metadata: Optional[Dict[str, Any]] = None


class UsageRecordResponse(BaseModel):
    """A usage record."""
    id: str
    user_id: str
    resource_type: str
    quantity: int
    metadata: Optional[Dict[str, Any]] = None
    recorded_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UsageTransactionResponse(BaseModel):
    """A usage transaction."""
    id: str
    user_id: str
    resource_type: str
    quantity: int
    timestamp: Optional[datetime] = None
    status: str = "completed"
    
    class Config:
        from_attributes = True


class UsageListResponse(BaseModel):
    """List of usage records."""
    items: List[UsageTransactionResponse]
    total: int
    skip: int = 0
    limit: int = 50


class UsageSummaryItem(BaseModel):
    """A usage summary item."""
    resource_type: str
    total_used: int
    limit: Optional[int] = None
    remaining: Optional[int] = None
    percentage: Optional[float] = None


class UsageSummaryResponse(BaseModel):
    """Usage summary."""
    user_id: str
    period: str
    items: List[UsageSummaryItem]
    last_reset: Optional[datetime] = None


class UsageCorrelationGroupResponse(BaseModel):
    """Usage correlation group."""
    id: str
    name: str
    resources: List[str]
    
    class Config:
        from_attributes = True


class UsageCorrelationListResponse(BaseModel):
    """List of usage correlation groups."""
    items: List[UsageCorrelationGroupResponse]
    total: int


class UsageStatsResponse(BaseModel):
    """Usage statistics."""
    resource_type: str
    total_used: int
    limit: Optional[int] = None
    remaining: Optional[int] = None
    period: Optional[str] = None
