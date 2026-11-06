
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[UUID] = mapped_column(
        primary_key=True
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    original_characters: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    questions: Mapped[list["DocumentQuestion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan"
    )


class DocumentQuestion(Base):
    __tablename__ = "document_questions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    document: Mapped["Document"] = relationship(
        back_populates="questions"
    )