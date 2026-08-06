import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.product_repository import ProductRepository
from app.domain.product import EnvironmentalFactor, Product

DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "data"


def seed_catalog(session: Session) -> None:
    repository = ProductRepository(session)
    for item in _read_json(DATA_DIRECTORY / "products.json"):
        repository.save_product(_create_product(item))


def seed_environmental_factors(session: Session) -> None:
    repository = ProductRepository(session)
    for item in _read_json(DATA_DIRECTORY / "environmental_factors.json"):
        repository.save_environmental_factor(_create_environmental_factor(item))


def initialize_data(session: Session) -> None:
    repository = ProductRepository(session)
    if repository.count_products() == 0:
        seed_catalog(session)
    if not repository.list_environmental_factors():
        seed_environmental_factors(session)


def _read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _create_product(item: dict[str, Any]) -> Product:
    return Product(
        id=item["id"],
        barcode=item["barcode"],
        barcode_raw=item["barcode"],
        name=item["name"],
        brand=item["brand"],
        category=item["category"],
        price_clp=item["price_clp"],
        package_grams=item["package_grams"],
        origin=item["origin"],
        packaging_type=item["packaging_type"],
        recyclable=item["recyclable"],
        certifications=tuple(item["certifications"]),
        social_indicator=item["social_indicator"],
        external_provider="local",
        external_id=None,
        updated_at=datetime.now(UTC),
    )


def _create_environmental_factor(item: dict[str, Any]) -> EnvironmentalFactor:
    return EnvironmentalFactor(
        category=item["category"],
        co2e_kg_per_kg=item["co2e_kg_per_kg"],
        source=item["source"],
        source_version=item["source_version"],
        confidence=item["confidence"],
        updated_at=datetime.now(UTC),
    )
