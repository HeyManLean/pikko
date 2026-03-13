from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from models.project import Project
    from models.storyboard import StoryboardPanel, Video


class Episode(Base, TimestampMixin):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(200))
    synopsis: Mapped[str | None] = mapped_column(Text)
    plot_details: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship("Project", back_populates="episodes")
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="episode", cascade="all, delete-orphan", order_by="Scene.number")
    video: Mapped[Video | None] = relationship("Video", back_populates="episode", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Episode {self.number}: {self.title!r}>"


class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(300))
    dialogue: Mapped[str | None] = mapped_column(Text)
    props: Mapped[str | None] = mapped_column(Text)
    characters_involved: Mapped[str | None] = mapped_column(Text)

    episode: Mapped[Episode] = relationship("Episode", back_populates="scenes")
    panels: Mapped[list[StoryboardPanel]] = relationship("StoryboardPanel", back_populates="scene", cascade="all, delete-orphan", order_by="StoryboardPanel.number")

    def __repr__(self) -> str:
        return f"<Scene {self.number} of episode={self.episode_id!r}>"
