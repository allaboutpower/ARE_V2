import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prompt(Base):
    """一筆使用者為某週產生的 prompt（含 Evidence Package），CSV 本身不存進 DB。"""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    week_index: Mapped[int] = mapped_column(Integer, nullable=False)
    week_date: Mapped[str] = mapped_column(String, nullable=False)
    evidence_package: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
