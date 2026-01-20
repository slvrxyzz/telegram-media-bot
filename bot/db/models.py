from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MediaContent(Base):
    __tablename__ = "media_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_file_unique_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_approved: Mapped[bool] = mapped_column(default=True)

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="media_tags",
        back_populates="media_items",
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    media_items: Mapped[list[MediaContent]] = relationship(
        "MediaContent",
        secondary="media_tags",
        back_populates="tags",
    )


class MediaTag(Base):
    __tablename__ = "media_tags"
    __table_args__ = (
        UniqueConstraint("media_id", "tag_id", name="uq_media_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media_content.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
    )

