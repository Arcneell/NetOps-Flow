"""
Knowledge Base Router for self-service articles and documentation.
Provides article management with search and feedback functionality.
Includes dynamic category management for organizing articles.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime, timezone
import re
import logging

from backend.core.database import get_db
from backend.core.security import get_current_user, has_permission
from backend import models, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ==================== CATEGORY ENDPOINTS ====================

@router.get("/categories", response_model=List[schemas.KnowledgeCategory])
def list_categories(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all knowledge base categories."""
    query = db.query(models.KnowledgeCategory)

    if not include_inactive:
        query = query.filter(models.KnowledgeCategory.is_active == True)

    categories = query.order_by(
        models.KnowledgeCategory.display_order,
        models.KnowledgeCategory.name
    ).all()

    return categories


@router.post("/categories", response_model=schemas.KnowledgeCategory)
def create_category(
    category_data: schemas.KnowledgeCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new knowledge base category (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check for duplicate name
    existing = db.query(models.KnowledgeCategory).filter(
        models.KnowledgeCategory.name == category_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    category = models.KnowledgeCategory(**category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)

    logger.info(f"Knowledge category '{category.name}' created by {current_user.username}")
    return category


@router.get("/categories/{category_id}", response_model=schemas.KnowledgeCategory)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific category by ID."""
    category = db.query(models.KnowledgeCategory).filter(
        models.KnowledgeCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.put("/categories/{category_id}", response_model=schemas.KnowledgeCategory)
def update_category(
    category_id: int,
    category_data: schemas.KnowledgeCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a knowledge base category (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    category = db.query(models.KnowledgeCategory).filter(
        models.KnowledgeCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for duplicate name if name is being changed
    update_data = category_data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != category.name:
        existing = db.query(models.KnowledgeCategory).filter(
            models.KnowledgeCategory.name == update_data["name"],
            models.KnowledgeCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")

    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    logger.info(f"Knowledge category '{category.name}' updated by {current_user.username}")
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a knowledge base category (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    category = db.query(models.KnowledgeCategory).filter(
        models.KnowledgeCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if there are articles using this category
    article_count = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.category_id == category_id
    ).count()

    if article_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {article_count} article(s). Move articles to another category first."
        )

    name = category.name
    db.delete(category)
    db.commit()

    logger.info(f"Knowledge category '{name}' deleted by {current_user.username}")
    return {"message": f"Category '{name}' deleted"}


def can_manage_knowledge(user: models.User) -> bool:
    """Check if user can manage knowledge base (tech, admin, superadmin)."""
    return user.role in ("tech", "admin", "superadmin")


def generate_slug(title: str, db: Session, existing_id: int = None) -> str:
    """Generate a unique URL-friendly slug from title."""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    # Check for uniqueness
    base_slug = slug
    counter = 1
    while True:
        query = db.query(models.KnowledgeArticle).filter(
            models.KnowledgeArticle.slug == slug
        )
        if existing_id:
            query = query.filter(models.KnowledgeArticle.id != existing_id)

        if not query.first():
            break

        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


# ==================== PUBLIC ENDPOINTS ====================

@router.get("/articles", response_model=schemas.PaginatedKnowledgeResponse)
def list_articles(
    category: Optional[str] = None,
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    published_only: bool = True,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List knowledge base articles with pagination."""
    query = db.query(models.KnowledgeArticle).options(
        joinedload(models.KnowledgeArticle.category_rel)
    )

    # Entity filtering for non-privileged users
    if not can_manage_knowledge(current_user) and current_user.entity_id:
        query = query.filter(
            or_(
                models.KnowledgeArticle.entity_id == current_user.entity_id,
                models.KnowledgeArticle.entity_id == None
            )
        )

    # Published filter (users see only published, tech/admin/superadmin see all)
    if published_only and not can_manage_knowledge(current_user):
        query = query.filter(models.KnowledgeArticle.is_published == True)

    # Internal articles only for tech/admin/superadmin
    if not can_manage_knowledge(current_user):
        query = query.filter(models.KnowledgeArticle.is_internal == False)

    # Category filter - support both category_id and legacy category string
    if category_id:
        query = query.filter(models.KnowledgeArticle.category_id == category_id)
    elif category:
        # Legacy: filter by string category name
        query = query.filter(models.KnowledgeArticle.category == category)

    # Tag filter (JSON array contains)
    if tag:
        query = query.filter(
            func.json_contains(models.KnowledgeArticle.tags, f'"{tag}"')
        )

    # Search in title, content, summary
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.KnowledgeArticle.title.ilike(search_term),
                models.KnowledgeArticle.summary.ilike(search_term),
                models.KnowledgeArticle.content.ilike(search_term)
            )
        )

    # Get total count
    total = query.count()

    # Get paginated results
    articles = query.order_by(
        models.KnowledgeArticle.view_count.desc(),
        models.KnowledgeArticle.created_at.desc()
    ).offset(skip).limit(limit).all()

    items = [
        schemas.KnowledgeArticleBrief(
            id=a.id,
            title=a.title,
            slug=a.slug,
            summary=a.summary,
            category=a.category,
            category_id=a.category_id,
            category_name=a.category_rel.name if a.category_rel else None,
            is_published=a.is_published,
            is_internal=a.is_internal,
            view_count=a.view_count,
            created_at=a.created_at
        ) for a in articles
    ]

    return schemas.PaginatedKnowledgeResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/articles/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get list of available categories."""
    query = db.query(models.KnowledgeArticle.category).filter(
        models.KnowledgeArticle.category != None,
        models.KnowledgeArticle.is_published == True
    )

    if not can_manage_knowledge(current_user):
        query = query.filter(models.KnowledgeArticle.is_internal == False)

    categories = query.distinct().all()
    return [c[0] for c in categories if c[0]]


@router.get("/articles/popular", response_model=List[schemas.KnowledgeArticleBrief])
def get_popular_articles(
    limit: int = Query(default=5, le=20),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get most viewed articles."""
    query = db.query(models.KnowledgeArticle).options(
        joinedload(models.KnowledgeArticle.category_rel)
    ).filter(
        models.KnowledgeArticle.is_published == True
    )

    if not can_manage_knowledge(current_user):
        query = query.filter(models.KnowledgeArticle.is_internal == False)

    articles = query.order_by(
        models.KnowledgeArticle.view_count.desc()
    ).limit(limit).all()

    return [
        schemas.KnowledgeArticleBrief(
            id=a.id,
            title=a.title,
            slug=a.slug,
            summary=a.summary,
            category=a.category,
            category_id=a.category_id,
            category_name=a.category_rel.name if a.category_rel else None,
            is_published=a.is_published,
            view_count=a.view_count,
            created_at=a.created_at
        ) for a in articles
    ]


@router.get("/articles/{slug}", response_model=schemas.KnowledgeArticleFull)
def get_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get article by slug."""
    article = db.query(models.KnowledgeArticle).options(
        joinedload(models.KnowledgeArticle.author),
        joinedload(models.KnowledgeArticle.last_editor),
        joinedload(models.KnowledgeArticle.category_rel)
    ).filter(models.KnowledgeArticle.slug == slug).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Access control
    if not article.is_published and not can_manage_knowledge(current_user):
        raise HTTPException(status_code=404, detail="Article not found")

    if article.is_internal and not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Entity check
    if not can_manage_knowledge(current_user) and current_user.entity_id:
        if article.entity_id and article.entity_id != current_user.entity_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Increment view count
    article.view_count += 1
    db.commit()

    return schemas.KnowledgeArticleFull(
        id=article.id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        summary=article.summary,
        category=article.category,
        category_id=article.category_id,
        category_name=article.category_rel.name if article.category_rel else None,
        tags=article.tags or [],
        is_published=article.is_published,
        is_internal=article.is_internal,
        author_id=article.author_id,
        last_editor_id=article.last_editor_id,
        view_count=article.view_count,
        helpful_count=article.helpful_count,
        not_helpful_count=article.not_helpful_count,
        version=article.version,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_at=article.published_at,
        entity_id=article.entity_id,
        author_name=article.author.username if article.author else None,
        last_editor_name=article.last_editor.username if article.last_editor else None
    )


@router.post("/articles/{article_id}/feedback")
def submit_feedback(
    article_id: int,
    feedback: schemas.KnowledgeArticleFeedback,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Submit helpful/not helpful feedback for an article."""
    article = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.id == article_id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if feedback.helpful:
        article.helpful_count += 1
    else:
        article.not_helpful_count += 1

    db.commit()

    return {"message": "Feedback recorded"}


# ==================== ADMIN ENDPOINTS ====================

@router.post("/articles", response_model=schemas.KnowledgeArticle)
def create_article(
    article_data: schemas.KnowledgeArticleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new knowledge base article (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    slug = generate_slug(article_data.title, db)

    article = models.KnowledgeArticle(
        title=article_data.title,
        slug=slug,
        content=article_data.content,
        summary=article_data.summary,
        category=article_data.category,
        category_id=article_data.category_id,
        tags=article_data.tags,
        is_published=article_data.is_published,
        is_internal=article_data.is_internal,
        author_id=current_user.id,
        entity_id=article_data.entity_id,
        published_at=datetime.now(timezone.utc) if article_data.is_published else None
    )

    db.add(article)
    db.commit()
    db.refresh(article)

    # Update category article count
    if article.category_id:
        _update_category_article_count(db, article.category_id)

    logger.info(f"Knowledge article '{article.title}' created by {current_user.username}")
    return article


def _update_category_article_count(db: Session, category_id: int):
    """Update the article_count for a category."""
    count = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.category_id == category_id
    ).count()
    db.query(models.KnowledgeCategory).filter(
        models.KnowledgeCategory.id == category_id
    ).update({"article_count": count})
    db.commit()


@router.put("/articles/{article_id}", response_model=schemas.KnowledgeArticle)
def update_article(
    article_id: int,
    article_data: schemas.KnowledgeArticleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update an article (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    article = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.id == article_id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = article_data.model_dump(exclude_unset=True)

    # Track category changes for count update
    old_category_id = article.category_id
    new_category_id = update_data.get("category_id", old_category_id)

    # Regenerate slug if title changed
    if "title" in update_data:
        update_data["slug"] = generate_slug(update_data["title"], db, article_id)

    # Handle publishing
    if "is_published" in update_data:
        if update_data["is_published"] and not article.published_at:
            update_data["published_at"] = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(article, field, value)

    article.last_editor_id = current_user.id
    article.version += 1

    db.commit()
    db.refresh(article)

    # Update category article counts if category changed
    if old_category_id != new_category_id:
        if old_category_id:
            _update_category_article_count(db, old_category_id)
        if new_category_id:
            _update_category_article_count(db, new_category_id)

    logger.info(f"Knowledge article '{article.title}' updated by {current_user.username}")
    return article


@router.delete("/articles/{article_id}")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete an article (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    article = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.id == article_id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    title = article.title
    category_id = article.category_id
    db.delete(article)
    db.commit()

    # Update category article count
    if category_id:
        _update_category_article_count(db, category_id)

    logger.info(f"Knowledge article '{title}' deleted by {current_user.username}")
    return {"message": f"Article '{title}' deleted"}


@router.post("/articles/{article_id}/publish")
def publish_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Publish an article (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    article = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.id == article_id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.is_published = True
    article.published_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": f"Article '{article.title}' published"}


@router.post("/articles/{article_id}/unpublish")
def unpublish_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Unpublish an article (admin only)."""
    if not can_manage_knowledge(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    article = db.query(models.KnowledgeArticle).filter(
        models.KnowledgeArticle.id == article_id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.is_published = False
    db.commit()

    return {"message": f"Article '{article.title}' unpublished"}
