from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Product:
    id: str
    barcode: str
    barcode_raw: str
    name: str
    brand: str
    category: str
    price_clp: int | None
    package_grams: float | None
    origin: str | None
    packaging_type: str | None
    recyclable: bool | None
    certifications: tuple[str, ...]
    social_indicator: str | None
    external_provider: str
    external_id: str | None
    updated_at: datetime

    @property
    def is_complete(self) -> bool:
        return (
            self.price_clp is not None
            and self.price_clp > 0
            and self.package_grams is not None
            and self.package_grams > 0
            and self.category != "other"
        )


@dataclass(frozen=True)
class EnvironmentalFactor:
    category: str
    co2e_kg_per_kg: float
    source: str
    source_version: str
    confidence: str
    updated_at: datetime
