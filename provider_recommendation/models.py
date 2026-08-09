from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ProviderRecommendation(Base):
    __tablename__ = "provider_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(Integer, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(Text)
    recommended_provider: Mapped[str] = mapped_column(String(100))
    expected_savings_usd: Mapped[float] = mapped_column(Float)
    expected_speedup_percent: Mapped[float] = mapped_column(Float)
    version: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
