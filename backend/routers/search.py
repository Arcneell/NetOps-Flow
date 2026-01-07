"""
Global Search Router - Unified search across multiple resources.
Provides a single endpoint to search equipment, tickets, knowledge articles, and more.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, and_, String
from typing import Optional, List
from datetime import datetime
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, has_permission
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
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated types to search: equipment,tickets,articles,subnets,contracts,software"),
    limit: int = Query(default=30, le=100, description="Max results per type"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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
    search_term_exact = q.lower()  # For relevance scoring
    results: List[SearchResultItem] = []
    type_counts = {}

    # Determine which types to search
    allowed_types = {"equipment", "tickets", "articles", "subnets", "contracts", "software"}
    if types:
        search_types = set(types.split(",")) & allowed_types
    else:
        search_types = allowed_types

    # Check user permissions for different search types
    can_search_inventory = has_permission(current_user, "inventory")
    can_search_ipam = has_permission(current_user, "ipam")
    can_search_contracts = has_permission(current_user, "contracts")
    can_search_software = has_permission(current_user, "software")
    can_search_knowledge = has_permission(current_user, "knowledge")

    logger.debug(f"Search permissions for {current_user.username} (role={current_user.role}): "
                 f"inventory={can_search_inventory}, ipam={can_search_ipam}, "
                 f"contracts={can_search_contracts}, software={can_search_software}, "
                 f"knowledge={can_search_knowledge}")

    # ==================== SEARCH EQUIPMENT ====================
    if "equipment" in search_types and can_search_inventory:
        equipment_query = db.query(models.Equipment).options(
            joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type)
        ).filter(
            or_(
                func.lower(func.coalesce(models.Equipment.name, '')).like(search_term),
                func.lower(func.coalesce(models.Equipment.serial_number, '')).like(search_term),
                func.lower(func.coalesce(models.Equipment.asset_tag, '')).like(search_term),
                func.lower(func.coalesce(models.Equipment.notes, '')).like(search_term)
            )
        )

        if current_user.entity_id:
            equipment_query = equipment_query.filter(
                models.Equipment.entity_id == current_user.entity_id
            )

        equipment = equipment_query.limit(limit).all()
        type_counts["equipment"] = len(equipment)
        logger.debug(f"Equipment search: found {len(equipment)} results")

        for eq in equipment:
            # Get equipment type through model relationship
            eq_type_name = None
            if eq.model and eq.model.equipment_type:
                eq_type_name = eq.model.equipment_type.name
            # Calculate relevance score
            score = 0.5
            if eq.name and search_term_exact in eq.name.lower():
                score = 1.0 if eq.name.lower().startswith(search_term_exact) else 0.8
            results.append(SearchResultItem(
                id=eq.id,
                type="equipment",
                title=eq.name,
                subtitle=eq_type_name,
                description=f"S/N: {eq.serial_number}" if eq.serial_number else None,
                status=eq.status,
                url=f"/inventory?id={eq.id}",
                score=score
            ))

    # ==================== SEARCH TICKETS ====================
    # Note: We only search ticket_number and title, NOT description
    # This prevents irrelevant results from matching common words in descriptions
    if "tickets" in search_types:
        tickets_query = db.query(models.Ticket).filter(
            or_(
                func.lower(func.coalesce(models.Ticket.ticket_number, '')).like(search_term),
                func.lower(func.coalesce(models.Ticket.title, '')).like(search_term)
            )
        )

        # Access control - users only see their own tickets, tech/admin/superadmin see all
        can_see_all_tickets = current_user.role in ("tech", "admin", "superadmin")
        if not can_see_all_tickets:
            tickets_query = tickets_query.filter(
                models.Ticket.requester_id == current_user.id
            )
        elif can_see_all_tickets and current_user.entity_id:
            tickets_query = tickets_query.filter(
                models.Ticket.entity_id == current_user.entity_id
            )

        tickets = tickets_query.limit(limit).all()
        type_counts["tickets"] = len(tickets)
        logger.debug(f"Tickets search: found {len(tickets)} results")

        for t in tickets:
            # Calculate relevance score
            score = 0.5
            if t.title and search_term_exact in t.title.lower():
                score = 1.0 if t.title.lower().startswith(search_term_exact) else 0.8
            elif t.ticket_number and search_term_exact in t.ticket_number.lower():
                score = 0.9
            results.append(SearchResultItem(
                id=t.id,
                type="ticket",
                title=f"{t.ticket_number}: {t.title}",
                subtitle=f"{t.ticket_type.capitalize()} - {t.priority.capitalize()}",
                description=t.description[:100] if t.description else None,
                status=t.status,
                url=f"/tickets?id={t.id}",
                score=score
            ))

    # ==================== SEARCH KNOWLEDGE ARTICLES ====================
    if "articles" in search_types and can_search_knowledge:
        articles_query = db.query(models.KnowledgeArticle).filter(
            models.KnowledgeArticle.is_published == True,
            or_(
                func.lower(func.coalesce(models.KnowledgeArticle.title, '')).like(search_term),
                func.lower(func.coalesce(models.KnowledgeArticle.content, '')).like(search_term),
                func.lower(func.coalesce(models.KnowledgeArticle.summary, '')).like(search_term)
            )
        )

        # Only tech/admin/superadmin can see internal articles
        can_see_internal = current_user.role in ("tech", "admin", "superadmin")
        if not can_see_internal:
            articles_query = articles_query.filter(
                models.KnowledgeArticle.is_internal == False
            )

        articles = articles_query.limit(limit).all()
        type_counts["articles"] = len(articles)
        logger.debug(f"Articles search: found {len(articles)} results")

        for a in articles:
            # Calculate relevance score
            score = 0.5
            if a.title and search_term_exact in a.title.lower():
                score = 1.0 if a.title.lower().startswith(search_term_exact) else 0.8
            results.append(SearchResultItem(
                id=a.id,
                type="article",
                title=a.title,
                subtitle=a.category,
                description=a.summary[:100] if a.summary else None,
                status="published" if a.is_published else "draft",
                url=f"/knowledge/{a.slug}",
                score=score
            ))

    # ==================== SEARCH SUBNETS ====================
    if "subnets" in search_types and can_search_ipam:
        # Cast cidr to text for LIKE search (cidr is inet type in PostgreSQL)
        subnets_query = db.query(models.Subnet).filter(
            or_(
                func.lower(func.cast(models.Subnet.cidr, String)).like(search_term),
                func.lower(func.coalesce(models.Subnet.name, '')).like(search_term),
                func.lower(func.coalesce(models.Subnet.description, '')).like(search_term)
            )
        )

        if current_user.entity_id:
            subnets_query = subnets_query.filter(
                models.Subnet.entity_id == current_user.entity_id
            )

        subnets = subnets_query.limit(limit).all()
        type_counts["subnets"] = len(subnets)
        logger.debug(f"Subnets search: found {len(subnets)} results")

        for s in subnets:
            # Calculate relevance score
            score = 0.5
            cidr_str = str(s.cidr) if s.cidr else ""
            if search_term_exact in cidr_str.lower():
                score = 1.0 if cidr_str.lower().startswith(search_term_exact) else 0.8
            elif s.name and search_term_exact in s.name.lower():
                score = 0.9
            results.append(SearchResultItem(
                id=s.id,
                type="subnet",
                title=cidr_str,
                subtitle=s.name,
                description=s.description[:100] if s.description else None,
                status=None,
                url=f"/ipam?subnet={s.id}",
                score=score
            ))

    # ==================== SEARCH CONTRACTS ====================
    if "contracts" in search_types and can_search_contracts:
        contracts_query = db.query(models.Contract).options(
            joinedload(models.Contract.supplier)
        ).filter(
            or_(
                func.lower(func.coalesce(models.Contract.name, '')).like(search_term),
                func.lower(func.coalesce(models.Contract.contract_number, '')).like(search_term),
                func.lower(func.coalesce(models.Contract.contract_type, '')).like(search_term),
                func.lower(func.coalesce(models.Contract.notes, '')).like(search_term)
            )
        )

        if current_user.entity_id:
            contracts_query = contracts_query.filter(
                models.Contract.entity_id == current_user.entity_id
            )

        contracts = contracts_query.limit(limit).all()
        type_counts["contracts"] = len(contracts)
        logger.debug(f"Contracts search: found {len(contracts)} results")

        for c in contracts:
            # Calculate relevance score
            score = 0.5
            if c.name and search_term_exact in c.name.lower():
                score = 1.0 if c.name.lower().startswith(search_term_exact) else 0.8
            elif c.contract_number and search_term_exact in c.contract_number.lower():
                score = 0.9
            # Get supplier name if available
            supplier_name = c.supplier.name if c.supplier else None
            subtitle_parts = [c.contract_type.capitalize() if c.contract_type else ""]
            if supplier_name:
                subtitle_parts.append(supplier_name)
            results.append(SearchResultItem(
                id=c.id,
                type="contract",
                title=c.name,
                subtitle=" - ".join(filter(None, subtitle_parts)),
                description=c.contract_number,
                status=None,
                url=f"/contracts?id={c.id}",
                score=score
            ))

    # ==================== SEARCH SOFTWARE ====================
    if "software" in search_types and can_search_software:
        software_query = db.query(models.Software).filter(
            or_(
                func.lower(func.coalesce(models.Software.name, '')).like(search_term),
                func.lower(func.coalesce(models.Software.publisher, '')).like(search_term),
                func.lower(func.coalesce(models.Software.notes, '')).like(search_term)
            )
        )

        if current_user.entity_id:
            software_query = software_query.filter(
                models.Software.entity_id == current_user.entity_id
            )

        software = software_query.limit(limit).all()
        type_counts["software"] = len(software)
        logger.debug(f"Software search: found {len(software)} results")

        for sw in software:
            # Calculate relevance score
            score = 0.5
            if sw.name and search_term_exact in sw.name.lower():
                score = 1.0 if sw.name.lower().startswith(search_term_exact) else 0.8
            elif sw.publisher and search_term_exact in sw.publisher.lower():
                score = 0.7
            results.append(SearchResultItem(
                id=sw.id,
                type="software",
                title=sw.name,
                subtitle=sw.publisher,
                description=f"v{sw.version}" if sw.version else None,
                status=None,
                url=f"/software?id={sw.id}",
                score=score
            ))

    # Sort results by score (highest first)
    results.sort(key=lambda x: x.score, reverse=True)

    logger.info(f"Global search by {current_user.username}: '{q}' - {len(results)} results")

    return SearchResults(
        query=q,
        total=len(results),
        results=results,
        by_type=type_counts
    )
