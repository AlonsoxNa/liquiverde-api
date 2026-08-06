from datetime import UTC, datetime

from app.adapters.agribalyse import (
    CATEGORY_QUERIES,
    AgribalyseClient,
    AgribalyseServiceError,
)
from app.adapters.database import Database
from app.adapters.product_repository import ProductRepository
from app.application.catalog_seed import seed_environmental_factors
from app.config import load_settings
from app.domain.product import EnvironmentalFactor


def main() -> None:
    settings = load_settings()
    database = Database(settings.database_url)
    database.create_schema()
    client = AgribalyseClient(
        settings.agribalyse_base_url,
        settings.external_api_timeout_seconds,
        settings.external_api_user_agent,
    )
    with database.session_factory() as session:
        seed_environmental_factors(session)
        repository = ProductRepository(session)
        for category in CATEGORY_QUERIES:
            try:
                co2e_kg_per_kg = client.fetch_category_factor(category)
            except AgribalyseServiceError:
                continue
            repository.save_environmental_factor(
                EnvironmentalFactor(
                    category=category,
                    co2e_kg_per_kg=co2e_kg_per_kg,
                    source="AGRIBALYSE",
                    source_version="3.2",
                    confidence="medium",
                    updated_at=datetime.now(UTC),
                )
            )


if __name__ == "__main__":
    main()
