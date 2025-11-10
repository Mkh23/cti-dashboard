from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AdminAnnouncement, User
from .me import get_current_user
from .admin import require_admin

router = APIRouter()


class AnnouncementPublicOut(BaseModel):
    id: UUID
    author_name: Optional[str]
    subject: str
    content_html: str
    created_at: datetime


class AnnouncementAdminOut(AnnouncementPublicOut):
    show_on_home: bool
    pinned: bool


class AnnouncementCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    content_html: str = Field(..., min_length=1)
    show_on_home: bool = False
    pinned: bool = False


class AnnouncementUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content_html: Optional[str] = Field(default=None, min_length=1)
    show_on_home: Optional[bool] = None
    pinned: Optional[bool] = None


@router.get("/announcements", response_model=List[AnnouncementPublicOut])
def list_public_announcements(db: Session = Depends(get_db)):
    announcements = (
        db.query(AdminAnnouncement)
        .join(User)
        .filter(AdminAnnouncement.show_on_home.is_(True))
        .order_by(AdminAnnouncement.pinned.desc(), AdminAnnouncement.created_at.desc())
        .all()
    )
    return [
        AnnouncementPublicOut(
            id=a.id,
            author_name=a.author.full_name or a.author.email,
            subject=a.subject,
            content_html=a.content_html,
            created_at=a.created_at,
        )
        for a in announcements
    ]


@router.get("/admin/announcements", response_model=List[AnnouncementAdminOut])
def list_admin_announcements(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current, db)
    announcements = (
        db.query(AdminAnnouncement)
        .join(User)
        .order_by(AdminAnnouncement.pinned.desc(), AdminAnnouncement.created_at.desc())
        .all()
    )
    return [
        AnnouncementAdminOut(
            id=a.id,
            author_name=a.author.full_name or a.author.email,
            subject=a.subject,
            content_html=a.content_html,
            created_at=a.created_at,
            show_on_home=a.show_on_home,
            pinned=a.pinned,
        )
        for a in announcements
    ]


@router.post("/admin/announcements", response_model=AnnouncementAdminOut)
def create_announcement(
    payload: AnnouncementCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current, db)
    announcement = AdminAnnouncement(
        user_id=current.id,
        subject=payload.subject,
        content_html=payload.content_html,
        show_on_home=payload.show_on_home,
        pinned=payload.pinned,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return AnnouncementAdminOut(
        id=announcement.id,
        author_name=current.full_name or current.email,
        subject=announcement.subject,
        content_html=announcement.content_html,
        created_at=announcement.created_at,
        show_on_home=announcement.show_on_home,
        pinned=announcement.pinned,
    )


@router.put("/admin/announcements/{announcement_id}", response_model=AnnouncementAdminOut)
def update_announcement(
    announcement_id: UUID,
    payload: AnnouncementUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current, db)
    announcement = db.query(AdminAnnouncement).filter(AdminAnnouncement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if payload.subject is not None:
        announcement.subject = payload.subject
    if payload.content_html is not None:
        announcement.content_html = payload.content_html
    if payload.show_on_home is not None:
        announcement.show_on_home = payload.show_on_home
    if payload.pinned is not None:
        announcement.pinned = payload.pinned

    db.commit()
    db.refresh(announcement)

    return AnnouncementAdminOut(
        id=announcement.id,
        author_name=announcement.author.full_name or announcement.author.email,
        subject=announcement.subject,
        content_html=announcement.content_html,
        created_at=announcement.created_at,
        show_on_home=announcement.show_on_home,
        pinned=announcement.pinned,
    )
