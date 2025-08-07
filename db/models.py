"""SQLAlchemy models for the skin tracking pipeline."""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Image(Base):
    __tablename__ = "images"

    image_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    source: Mapped[str] = mapped_column(String, default="telegram")
    bucket_path: Mapped[str] = mapped_column(String)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    landmarks: Mapped["FaceLandmarks"] = relationship(back_populates="image", uselist=False)
    lesions: Mapped[List["Lesion"]] = relationship(back_populates="image")


class FaceLandmarks(Base):
    __tablename__ = "face_landmarks"

    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.image_id", ondelete="CASCADE"), PGUUID(as_uuid=True), primary_key=True)
    model: Mapped[str] = mapped_column(String, default="mediapipe_face_mesh")
    landmarks: Mapped[dict] = mapped_column(JSON)
    regions: Mapped[dict | None] = mapped_column(JSON)
    contour_heatmap_path: Mapped[str | None] = mapped_column(String)

    image: Mapped[Image] = relationship(back_populates="landmarks")


class Lesion(Base):
    __tablename__ = "lesions"

    lesion_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.image_id", ondelete="CASCADE"))
    detector: Mapped[str] = mapped_column(String)
    bbox: Mapped[dict] = mapped_column(JSON)
    mask_path: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String, default="pimple")
    region: Mapped[str | None] = mapped_column(String)
    area_px: Mapped[int | None] = mapped_column(Integer)
    redness_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    image: Mapped[Image] = relationship(back_populates="lesions")


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    session_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text)

    images: Mapped[List["SessionImage"]] = relationship(back_populates="session")


class SessionImage(Base):
    __tablename__ = "session_images"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.session_id", ondelete="CASCADE"), primary_key=True)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.image_id", ondelete="CASCADE"), primary_key=True)

    session: Mapped[Session] = relationship(back_populates="images")
    image: Mapped[Image] = relationship()


__all__ = ["Base", "Image", "FaceLandmarks", "Lesion", "Session", "SessionImage"]
