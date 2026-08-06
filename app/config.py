from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...]
    database_url: str
    open_food_facts_base_url: str
    open_prices_base_url: str
    agribalyse_base_url: str
    external_api_timeout_seconds: float
    external_api_user_agent: str


def load_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    return Settings(
        cors_origins=origins,
        database_url=getenv("DATABASE_URL", "sqlite:///./liquiverde.db"),
        open_food_facts_base_url=getenv(
            "OPEN_FOOD_FACTS_BASE_URL",
            "https://world.openfoodfacts.org/api/v3.6",
        ).rstrip("/"),
        open_prices_base_url=getenv(
            "OPEN_PRICES_BASE_URL",
            "https://prices.openfoodfacts.org/api/v1",
        ).rstrip("/"),
        agribalyse_base_url=getenv(
            "AGRIBALYSE_BASE_URL",
            "https://data.ademe.fr/data-fair/api/v1/datasets/agribalyse-31-synthese",
        ).rstrip("/"),
        external_api_timeout_seconds=float(getenv("EXTERNAL_API_TIMEOUT_SECONDS", "5")),
        external_api_user_agent=getenv(
            "EXTERNAL_API_USER_AGENT",
            "LiquiVerde/0.1 (https://github.com/AlonsoxNa/liquiverde-api)",
        ),
    )
