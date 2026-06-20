"""Internal Agent Runtime routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.application.use_cases.agent_runtime_use_cases import AgentRuntimeUseCases
from app.domain import AgentRuntimeError, AgentRuntimeNotFoundError, InternalContext
from app.presentation.deps import get_agent_runtime_use_cases, get_internal_context
from app.presentation.schemas.agent_runtime_schemas import (
    ConfirmationResponse,
    RuntimeCatalogItemCreateRequest,
    RunCreateRequest,
    RunResponse,
)


router = APIRouter(prefix="/internal/agent-runtime/v1")


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    body: RunCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> RunResponse:
    run = await use_cases.create_run(
        context=context,
        session_id=body.session_id,
        input_message_id=body.input_message_id,
        prompt=body.prompt,
        channel=body.channel,
        metadata=body.metadata,
        idempotency_key=idempotency_key,
    )
    return RunResponse.from_domain(run)


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> RunResponse:
    try:
        run = await use_cases.get_run(context=context, run_id=run_id)
    except AgentRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return RunResponse.from_domain(run)


@router.get("/settings")
async def get_runtime_settings(
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> dict:
    return await use_cases.get_runtime_settings(context=context)


@router.post("/settings/agents", status_code=status.HTTP_201_CREATED)
async def create_runtime_agent(
    body: RuntimeCatalogItemCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> dict:
    return await _create_catalog_item(
        collection="agents",
        body=body,
        idempotency_key=idempotency_key,
        context=context,
        use_cases=use_cases,
    )


@router.post("/settings/skills", status_code=status.HTTP_201_CREATED)
async def create_runtime_skill(
    body: RuntimeCatalogItemCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> dict:
    return await _create_catalog_item(
        collection="skills",
        body=body,
        idempotency_key=idempotency_key,
        context=context,
        use_cases=use_cases,
    )


@router.post("/settings/tools", status_code=status.HTTP_201_CREATED)
async def create_runtime_tool(
    body: RuntimeCatalogItemCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> dict:
    return await _create_catalog_item(
        collection="tools",
        body=body,
        idempotency_key=idempotency_key,
        context=context,
        use_cases=use_cases,
    )


@router.post("/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> RunResponse:
    try:
        run = await use_cases.cancel_run(context=context, run_id=run_id)
    except AgentRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code}) from exc
    return RunResponse.from_domain(run)


async def _create_catalog_item(
    *,
    collection: str,
    body: RuntimeCatalogItemCreateRequest,
    idempotency_key: str,
    context: InternalContext,
    use_cases: AgentRuntimeUseCases,
) -> dict:
    try:
        return await use_cases.create_runtime_catalog_item(
            context=context,
            collection=collection,
            payload=body.to_payload(),
            idempotency_key=idempotency_key,
        )
    except AgentRuntimeError as exc:
        status_code = status.HTTP_409_CONFLICT if exc.code == "idempotency_conflict" else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@router.post(
    "/runs/{run_id}/confirmations/{confirmation_id}/confirm",
    response_model=ConfirmationResponse,
)
async def confirm_confirmation(
    run_id: str,
    confirmation_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> ConfirmationResponse:
    return await _resolve_confirmation(
        run_id=run_id,
        confirmation_id=confirmation_id,
        decision="confirmed",
        context=context,
        use_cases=use_cases,
    )


@router.post(
    "/runs/{run_id}/confirmations/{confirmation_id}/cancel",
    response_model=ConfirmationResponse,
)
async def cancel_confirmation(
    run_id: str,
    confirmation_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentRuntimeUseCases = Depends(get_agent_runtime_use_cases),
) -> ConfirmationResponse:
    return await _resolve_confirmation(
        run_id=run_id,
        confirmation_id=confirmation_id,
        decision="cancelled",
        context=context,
        use_cases=use_cases,
    )


async def _resolve_confirmation(
    *,
    run_id: str,
    confirmation_id: str,
    decision: str,
    context: InternalContext,
    use_cases: AgentRuntimeUseCases,
) -> ConfirmationResponse:
    try:
        confirmation = await use_cases.resolve_confirmation(
            context=context,
            run_id=run_id,
            confirmation_id=confirmation_id,
            decision=decision,
        )
    except AgentRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code}) from exc
    return ConfirmationResponse.from_domain(confirmation)
