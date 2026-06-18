"""MS365 provider routes for legacy OAuth and sync operations."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status

from app.application.use_cases.ms365_provider_use_cases import MS365ProviderUseCases
from app.middleware.auth import get_current_user
from app.presentation.deps import get_ms365_provider_use_cases
from app.presentation.schemas.provider_ms365_schemas import (
    MS365AuthUrlResponse,
    MS365ConnectionResponse,
    SyncedEmailResponse,
    SyncedEmailListResponse,
    SyncedEventResponse,
    SyncedEventListResponse,
    SyncStatusResponse,
    EmailAiInsightResponse,
    SendEmailRequest,
    ReplyEmailRequest,
    ForwardEmailRequest,
)

router = APIRouter(prefix="/api/v1/provider/ms365")

@router.get('/auth-url', response_model=MS365AuthUrlResponse)
async def get_auth_url(
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.get_auth_url(current_user)

@router.get('/callback')
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.oauth_callback(request, code, state)

@router.get('/connection', response_model=Optional[MS365ConnectionResponse])
async def get_connection(
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.get_connection(request, current_user)

@router.delete('/connection', status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.disconnect(request, current_user)

@router.post('/sync', response_model=SyncStatusResponse)
async def force_sync(
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.force_sync(request, current_user)

@router.get('/emails', response_model=SyncedEmailListResponse)
async def list_emails(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    smart_label: Optional[str] = None,
    linked_contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.list_emails(request, skip, limit, folder, search, smart_label, linked_contact_id, current_user)

@router.get('/emails/{email_id}', response_model=SyncedEmailResponse)
async def get_email(
    email_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.get_email(email_id, request, current_user)

@router.post('/emails/{email_id}/ai-insights', response_model=EmailAiInsightResponse)
async def generate_email_ai_insights(
    email_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.generate_email_ai_insights(email_id, request, current_user)

@router.post('/emails/send')
async def send_email(
    send_request: SendEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.send_email(send_request, request, current_user)

@router.post('/emails/{email_id}/reply')
async def reply_email(
    email_id: str,
    reply_request: ReplyEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.reply_email(email_id, reply_request, request, current_user)

@router.post('/emails/{email_id}/forward')
async def forward_email(
    email_id: str,
    fwd_request: ForwardEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.forward_email(email_id, fwd_request, request, current_user)

@router.get('/events', response_model=SyncedEventListResponse)
async def list_events(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.list_events(request, skip, limit, from_date, to_date, current_user)

@router.get('/events/{event_id}', response_model=SyncedEventResponse)
async def get_event(
    event_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.get_event(event_id, request, current_user)

@router.post('/webhook')
async def ms365_webhook(
    request: Request,
    use_cases: MS365ProviderUseCases = Depends(get_ms365_provider_use_cases),
):
    return await use_cases.ms365_webhook(request)
