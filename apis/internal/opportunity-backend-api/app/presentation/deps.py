"""Presentation dependencies for Opportunity API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.opportunity_use_cases import OpportunityUseCases
from app.application.use_cases.quote_use_cases import QuoteUseCases
from app.events.publishers import publish_opportunity_created, publish_opportunity_updated
from app.infrastructure.database import get_db
from app.infrastructure.persistence.models.opportunity import Opportunity
from app.infrastructure.persistence.models.opportunity_product import OpportunityProduct
from app.infrastructure.persistence.models.quote import Quote
from app.infrastructure.persistence.opportunity_repository import OpportunityRepository
from app.infrastructure.persistence.quote_repository import QuoteRepository


def get_opportunity_use_cases(db: Session = Depends(get_db)) -> OpportunityUseCases:
    return OpportunityUseCases(
        repo=OpportunityRepository(db),
        create_opportunity_entity=Opportunity,
        create_line_entity=OpportunityProduct,
        publish_created=publish_opportunity_created,
        publish_updated=publish_opportunity_updated,
    )


def get_quote_use_cases(db: Session = Depends(get_db)) -> QuoteUseCases:
    return QuoteUseCases(
        repo=QuoteRepository(db),
        create_quote_entity=Quote,
    )
