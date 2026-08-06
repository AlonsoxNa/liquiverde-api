from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.product import Product


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    barcode: str
    name: str
    brand: str
    category: str
    price_clp: int | None
    package_grams: float | None
    origin: str | None
    packaging_type: str | None
    recyclable: bool | None
    certifications: list[str]
    social_indicator: str | None
    external_provider: str
    updated_at: datetime
    is_complete: bool

    @classmethod
    def from_product(cls, product: Product) -> ProductResponse:
        return cls(
            id=product.id,
            barcode=product.barcode,
            name=product.name,
            brand=product.brand,
            category=product.category,
            price_clp=product.price_clp,
            package_grams=product.package_grams,
            origin=product.origin,
            packaging_type=product.packaging_type,
            recyclable=product.recyclable,
            certifications=list(product.certifications),
            social_indicator=product.social_indicator,
            external_provider=product.external_provider,
            updated_at=product.updated_at,
            is_complete=product.is_complete,
        )


class ProductCollectionResponse(BaseModel):
    items: list[ProductResponse]


class SustainabilityAnalysisResponse(BaseModel):
    product: ProductResponse
    total_score: float
    economic_score: float
    environmental_score: float
    social_score: float
    subcomponents: dict[str, float]
    reasons: list[str]
    data_sources: list[str]
    confidence: str
    co2e_kg: float | None
    price_per_100g: float | None


class BarcodeLookupRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=32)


class ProductCompletionRequest(BaseModel):
    price_clp: int | None = Field(default=None, gt=0)
    package_grams: float | None = Field(default=None, gt=0)
    category: (
        Literal[
            "rice",
            "pasta",
            "milk_and_plant_drinks",
            "legumes",
            "coffee",
            "chocolate",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def require_change(self) -> ProductCompletionRequest:
        if (
            self.price_clp is None
            and self.package_grams is None
            and self.category is None
        ):
            raise ValueError("Debes proporcionar al menos un campo.")
        return self
