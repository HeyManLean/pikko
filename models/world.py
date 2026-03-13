from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from models.project import Project


class World(Base, TimestampMixin):
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    setting: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[str | None] = mapped_column(Text)
    atmosphere: Mapped[str | None] = mapped_column(Text)
    background_story: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship("Project", back_populates="world")

    def __repr__(self) -> str:
        return f"<World project={self.project_id!r}>"


class PlotOutline(Base, TimestampMixin):
    __tablename__ = "plot_outlines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    synopsis: Mapped[str | None] = mapped_column(Text)
    themes: Mapped[str | None] = mapped_column(Text)
    arc_structure: Mapped[str | None] = mapped_column(Text)
    total_episodes: Mapped[int | None] = mapped_column(Integer)

    project: Mapped[Project] = relationship("Project", back_populates="plot_outline")

    def __repr__(self) -> str:
        return f"<PlotOutline project={self.project_id!r}>"
