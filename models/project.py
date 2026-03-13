from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from models.character import Character
    from models.episode import Episode
    from models.world import PlotOutline, World


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    genre: Mapped[str | None] = mapped_column(String(100))
    target_audience: Mapped[str | None] = mapped_column(String(200))

    world: Mapped[World | None] = relationship("World", back_populates="project", uselist=False, cascade="all, delete-orphan")
    plot_outline: Mapped[PlotOutline | None] = relationship("PlotOutline", back_populates="project", uselist=False, cascade="all, delete-orphan")
    characters: Mapped[list[Character]] = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    episodes: Mapped[list[Episode]] = relationship("Episode", back_populates="project", cascade="all, delete-orphan", order_by="Episode.number")

    def __repr__(self) -> str:
        return f"<Project {self.name!r}>"
