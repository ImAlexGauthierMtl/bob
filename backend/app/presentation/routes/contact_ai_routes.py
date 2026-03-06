"""Contact AI routes — LLM-powered contact extraction.

Receives raw text (business card, email signature, etc.)
and uses Groq LLM to extract structured contact fields.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

import structlog

from app.presentation.routes.auth_routes import get_current_user
from app.agents.llm_client import llm_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/contacts")

CONTACT_EXTRACTION_PROMPT = """You are a contact information extraction agent.
Extract structured contact information from the following raw text.
The text may be a business card, email signature, LinkedIn snippet, or any unstructured text.

Return a JSON object with these fields (use null for missing fields):
- first_name (string, required)
- last_name (string, required)
- email (string or null)
- phone (string or null)
- mobile (string or null)
- job_title (string or null)
- department (string or null)
- linkedin_url (string or null)
- notes (string or null — any extra info that doesn't fit other fields)

Rules:
- If you cannot determine first_name or last_name, use "Unknown"
- Clean and normalize phone numbers
- Extract LinkedIn URLs if present
- Put company/organization mentions in notes
- Be precise — only extract what is clearly present in the text
- Return ONLY the JSON object, no explanation"""


class AiParseRequest(BaseModel):
    raw_text: str
    organization_id: Optional[str] = None


class AiParseResponse(BaseModel):
    extracted: dict
    confidence: float
    raw_text: str


@router.post("/ai-parse", response_model=AiParseResponse)
async def ai_parse_contact(
    request: AiParseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Parse raw text into structured contact fields using Groq LLM."""
    if not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="raw_text cannot be empty",
        )

    try:
        response = llm_client.chat(
            prompt=f"Extract contact info from this text:\n\n{request.raw_text}",
            system_prompt=CONTACT_EXTRACTION_PROMPT,
            json_mode=True,
            temperature=0.0,
            max_tokens=1024,
        )

        extracted = json.loads(response)

        # Ensure required fields
        extracted.setdefault("first_name", "Unknown")
        extracted.setdefault("last_name", "Unknown")

        # Inject organization_id if provided
        if request.organization_id:
            extracted["organization_id"] = request.organization_id

        # Calculate confidence based on how many fields were extracted
        fields = ["first_name", "last_name", "email", "phone", "mobile",
                  "job_title", "department", "linkedin_url"]
        filled = sum(1 for f in fields
                     if extracted.get(f) and extracted[f] != "Unknown")
        confidence = round(filled / len(fields), 2)

        logger.info(
            "contact_ai_parse",
            user=current_user["email"],
            fields_extracted=filled,
            confidence=confidence,
        )

        return AiParseResponse(
            extracted=extracted,
            confidence=confidence,
            raw_text=request.raw_text,
        )
    except json.JSONDecodeError as e:
        logger.error("contact_ai_parse_json_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bob could not parse the text. Try rephrasing.",
        )
    except Exception as e:
        logger.error("contact_ai_parse_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bob encountered an error while parsing. Please try again.",
        )
