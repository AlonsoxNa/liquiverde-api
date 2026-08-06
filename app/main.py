from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.database import Database
from app.application.catalog_seed import initialize_data
from app.config import Settings, load_settings
from app.http.errors import (
    ApiError,
    api_error_handler,
    request_validation_error_handler,
)
from app.http.product_routes import create_product_router
from app.http.shopping_list_routes import create_shopping_list_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    database = Database(resolved_settings.database_url)
    database.create_schema()
    with database.session_factory() as startup_session:
        initialize_data(startup_session)

    application = FastAPI(
        title="LiquiVerde API",
        description="Análisis de productos y optimización sostenible de compras.",
        version="0.1.0",
    )
    application.state.database = database
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_session() -> Iterator[Session]:
        yield from database.session()

    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )
    application.include_router(create_product_router(get_session, resolved_settings))
    application.include_router(create_shopping_list_router(get_session))

    @application.get("/health", tags=["health"])
    def health(
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return application


app = create_app()
