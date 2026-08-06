from app.adapters.database import Database
from app.application.catalog_seed import seed_catalog, seed_environmental_factors
from app.config import load_settings


def main() -> None:
    settings = load_settings()
    database = Database(settings.database_url)
    database.create_schema()
    with database.session_factory() as session:
        seed_catalog(session)
        seed_environmental_factors(session)


if __name__ == "__main__":
    main()
