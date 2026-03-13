from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from models.episode import Episode, Scene


class StoryboardPanel(Base, TimestampMixin):
    __tablename__ = "storyboard_panels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    camera_angle: Mapped[str | None] = mapped_column(String(100))
    dialogue: Mapped[str | None] = mapped_column(Text)
    sfx: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))

    scene: Mapped[Scene] = relationship("Scene", back_populates="panels")

    def __repr__(self) -> str:
        return f"<StoryboardPanel {self.number} of scene={self.scene_id!r}>"


class Video(Base, TimestampMixin):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    video_url: Mapped[str | None] = mapped_column(String(500))

    episode: Mapped[Episode] = relationship("Episode", back_populates="video")

    def __repr__(self) -> str:
        return f"<Video episode={self.episode_id!r} status={self.status!r}>"
