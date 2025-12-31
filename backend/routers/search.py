"""
Global Search Router - Unified search across multiple resources.
Provides a single endpoint to search equipment, tickets, knowledge articles, and more.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime
import logging

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend import models
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# ==================== RESPONSE MODELS ====================

class SearchResultItem(BaseModel):
    """Individual search result item."""
    id: int
    type: str  # equipment, ticket, article, subnet, contract, software
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    url: str  # Frontend route to navigate to
    score: float = 1.0  # Relevance score

    class Config:
        from_attributes = True


class SearchResults(BaseModel):
    """Global search results response."""
    query: str
    total: int
    results: List[SearchResultItem]
    by_type: dict  # Count by type


# ==================== GLOBAL SEARCH ENDPOINT ====================

@router.get("/", response_model=SearchResults)
def global_search(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated types to search: equipment,tickets,articles,subnets,contracts,software"),
    limit: int = Query(default=20, le=50, description="Max results per type"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Global search across multiple resource types.

    Searches:
    - Equipment (name, serial number, asset tag, notes)
    - Tickets (number, title, description)
    - Knowledge Articles (title, content, summary)
    - Subnets (CIDR, name, description)
    - Contracts (name, number, notes)
    - Software (name, publisher)
    """
    search_term = f"%{q.lower()}%"
    results: List[SearchResultItem] = []
    type_counts = {}

    # Determine which types to search
    allowed_types = {"equipment", "tickets", "articles", "subnets", "contracts", "software"}
    if types:
        search_types = set(types.split(",")) & allowed_types
    else:
        search_types = allowed_types

    is_admin = current_user.role == "admin"

    # ==================== SEARCH EQUIPMENT ====================
    if "equipment" in search_types and is_admin:
        equipment_query = db.query(models.Equipment).options(
            joinedload(models.Equipment.equipment_type)
        ).filter(
            or_(
                func.lower(models.Equipment.name).like(search_term),
                func.lower(models.Equipment.serial_number).like(search_term),
                func.lower(models.Equipment.asset_tag).like(search_term),
                func.lower(models.Equipment.notes).like(search_term)
            )
        )

        if current_user.entity_id:
            equipment_query = equipment_query.filter(
                models.Equipment.entity_id == current_user.entity_id
            )

        equipment = equipment_query.limit(limit).all()
        type_counts["equipment"] = len(equipment)

        for eq in equipment:
            results.append(SearchResultItem(
                id=eq.id,
                type="equipment",
                title=eq.name,
                subtitle=eq.equipment_type.name if eq.equipment_type else None,
                description=f"S/N: {eq.serial_number}" if eq.serial_number else None,
                status=eq.status,
                url=f"/inventory?id={eq.id}"
            ))

    # ==================== SEARCH TICKETS ====================
    if "tickets" in search_types:
        tickets_query = db.query(models.Ticket).filter(
            or_(
                func.lower(models.Ticket.ticket_number).like(search_term),
                func.lower(models.Ticket.title).like(search_term),
                func.lower(models.Ticket.description).like(search_term)
            )
        )

        # Access control
        if not is_admin:
            tickets_query = tickets_query.filter(
                models.Ticket.requester_id == current_user.id
            )
        elif current_user.entity_id:
            tickets_query = tickets_query.filter(
                models.Ticket.entity_id == current_user.entity_id
            )

        tickets = tickets_query.limit(limit).all()
        type_counts["tickets"] = len(tickets)

        for t in tickets:
            results.append(SearchResultItem(
                id=t.id,
                type="ticket",
                title=f"{t.ticket_number}: {t.title}",
                subtitle=f"{t.ticket_type.capitalize()} - {t.priority.capitalize()}",
                description=t.description[:100] if t.description else None,
                status=t.status,
                url=f"/tickets?id={t.id}"
            ))

    # ==================== SEARCH KNOWLEDGE ARTICLES ====================
    if "articles" in search_types:
        articles_query = db.query(models.KnowledgeArticle).filter(
            models.KnowledgeArticle.status == "published",
            or_(
                func.lower(models.KnowledgeArticle.title).like(search_term),
                func.lower(models.KnowledgeArticle.content).like(search_term),
                func.lower(models.KnowledgeArticle.summary).like(search_term)
            )
        )

        # Non-admin users can't see internal articles
        if not is_admin:
            articles_query = articles_query.filter(
                models.KnowledgeArticle.is_internal == False
            )

        articles = articles_query.limit(limit).all()
        type_counts["articles"] = len(articles)

        for a in articles:
            results.append(SearchResultItem(
                id=a.id,
                type="article",
                title=a.title,
                subtitle=a.category,
                description=a.summary[:100] if a.summary else None,
                status="published",
                url=f"/knowledge/{a.slug}"
            ))

    # ==================== SEARCH SUBNETS ====================
    if "subnets" in search_types and is_admin:
        subnets_query = db.query(models.Subnet).filter(
            or_(
                func.lower(models.Subnet.cidr).like(search_term),
                func.lower(models.Subnet.name).like(search_term),
                func.lower(models.Subnet.description).like(search_term)
            )
        )

        if current_user.entity_id:
            subnets_query = subnets_query.filter(
                models.Subnet.entity_id == current_user.entity_id
            )

        subnets = subnets_query.limit(limit).all()
        type_counts["subnets"] = len(subnets)

        for s in subnets:
            results.append(SearchResultItem(
                id=s.id,
                type="subnet",
                title=s.cidr,
                subtitle=s.name,
                description=s.description[:100] if s.description else None,
                status=None,
                url=f"/ipam?subnet={s.id}"
            ))

    # ==================== SEARCH CONTRACTS ====================
    if "contracts" in search_types and is_admin:
        contracts_query = db.query(models.Contract).filter(
            or_(
                func.lower(models.Contract.name).like(search_term),
                func.lower(models.Contract.contract_number).like(search_term),
                func.lower(models.Contract.notes).like(search_term)
            )
        )

        if current_user.entity_id:
            contracts_query = contracts_query.filter(
                models.Contract.entity_id == current_user.entity_id
            )

        contracts = contracts_query.limit(limit).all()
        type_counts["contracts"] = len(contracts)

        for c in contracts:
            results.append(SearchResultItem(
                id=c.id,
                type="contract",
                title=c.name,
                subtitle=f"{c.contract_type.capitalize()} - {c.status.capitalize()}",
                description=c.contract_number,
                status=c.status,
                url=f"/contracts?id={c.id}"
            ))

    # ==================== SEARCH SOFTWARE ====================
    if "software" in search_types and is_admin:
        software_query = db.query(models.Software).filter(
            or_(
                func.lower(models.Software.name).like(search_term),
                func.lower(models.Software.publisher).like(search_term),
                func.lower(models.Software.notes).like(search_term)
            )
        )

        if current_user.entity_id:
            software_query = software_query.filter(
                models.Software.entity_id == current_user.entity_id
            )

        software = software_query.limit(limit).all()
        type_counts["software"] = len(software)

        for sw in software:
            results.append(SearchResultItem(
                id=sw.id,
                type="software",
                title=sw.name,
                subtitle=sw.publisher,
                description=f"v{sw.version}" if sw.version else None,
                status=None,
                url=f"/software?id={sw.id}"
            ))

    logger.info(f"Global search by {current_user.username}: '{q}' - {len(results)} results")

    return SearchResults(
        query=q,
        total=len(results),
        results=results,
        by_type=type_counts
    )
