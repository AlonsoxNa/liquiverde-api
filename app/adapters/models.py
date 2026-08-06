from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.database import Base


class ProductRecord(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    barcode: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    barcode_raw: Mapped[str] = mapped_column(String(14))
    name: Mapped[str] = mapped_column(String(160), index=True)
    brand: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(64), index=True)
    price_clp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    packaging_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recyclable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    social_indicator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_provider: Mapped[str] = mapped_column(String(64), default="local")
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class EnvironmentalFactorRecord(Base):
    __tablename__ = "environmental_factors"

    category: Mapped[str] = mapped_column(String(64), primary_key=True)
    co2e_kg_per_kg: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(120))
    source_version: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
