"""Notifications API endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List notifications with pagination."""
    offset = (page - 1) * page_size

    # Build query
    query = select(Notification)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    # Get total count
    count_query = select(func.count()).select_from(Notification)
    if unread_only:
        count_query = count_query.where(Notification.read_at.is_(None))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get unread count
    unread_count_query = select(func.count()).select_from(Notification).where(
        Notification.read_at.is_(None)
    )
    unread_result = await db.execute(unread_count_query)
    unread_count = unread_result.scalar() or 0

    # Get notifications (unread first, then by date)
    query = (
        query.order_by(
            Notification.read_at.is_(None).desc(),  # Unread first
            desc(Notification.created_at),
        )
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Convert to response format
    items = []
    for notification in notifications:
        competitor_name = None
        if notification.competitor:
            competitor_name = notification.competitor.company_name

        items.append(
            NotificationResponse(
                id=notification.id,
                type=notification.type,
                title=notification.title,
                message=notification.message,
                competitor_id=notification.competitor_id,
                ad_id=notification.ad_id,
                ad_count=notification.ad_count,
                created_at=notification.created_at,
                read_at=notification.read_at,
                is_read=notification.is_read,
                competitor_name=competitor_name,
            )
        )

    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get count of unread notifications."""
    query = select(func.count()).select_from(Notification).where(
        Notification.read_at.is_(None)
    )
    result = await db.execute(query)
    count = result.scalar() or 0

    return {"unread_count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Get a specific notification by ID."""
    query = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    competitor_name = None
    if notification.competitor:
        competitor_name = notification.competitor.company_name

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        competitor_id=notification.competitor_id,
        ad_id=notification.ad_id,
        ad_count=notification.ad_count,
        created_at=notification.created_at,
        read_at=notification.read_at,
        is_read=notification.is_read,
        competitor_name=competitor_name,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a specific notification as read."""
    query = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notification)

    competitor_name = None
    if notification.competitor:
        competitor_name = notification.competitor.company_name

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        competitor_id=notification.competitor_id,
        ad_id=notification.ad_id,
        ad_count=notification.ad_count,
        created_at=notification.created_at,
        read_at=notification.read_at,
        is_read=notification.is_read,
        competitor_name=competitor_name,
    )


@router.post("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark all notifications as read."""
    stmt = (
        update(Notification)
        .where(Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)
    await db.commit()

    return {"marked_read": result.rowcount}


@router.post("/mark-read")
async def mark_notifications_read(
    request: NotificationMarkReadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark specific notifications as read."""
    if request.notification_ids:
        stmt = (
            update(Notification)
            .where(Notification.id.in_(request.notification_ids))
            .where(Notification.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )
    else:
        # Mark all as read
        stmt = (
            update(Notification)
            .where(Notification.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )

    result = await db.execute(stmt)
    await db.commit()

    return {"marked_read": result.rowcount}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a notification."""
    query = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()

    return {"status": "deleted"}


# Internal function to create notifications (used by other services)
async def create_notification(
    db: AsyncSession,
    notification_data: NotificationCreate,
) -> Notification:
    """Create a new notification (internal use)."""
    notification = Notification(
        type=notification_data.type,
        title=notification_data.title,
        message=notification_data.message,
        competitor_id=notification_data.competitor_id,
        ad_id=notification_data.ad_id,
        ad_count=notification_data.ad_count,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def create_new_ads_notification(
    db: AsyncSession,
    competitor_id: UUID,
    competitor_name: str,
    ad_count: int,
) -> Notification:
    """Create a notification for new ads retrieved."""
    notification_data = NotificationCreate(
        type="new_ads",
        title=f"New ads from {competitor_name}",
        message=f"{ad_count} new {'ad' if ad_count == 1 else 'ads'} retrieved from {competitor_name}",
        competitor_id=competitor_id,
        ad_count=ad_count,
    )
    return await create_notification(db, notification_data)
