from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.adapters.open_food_facts import ExternalServiceError, OpenFoodFactsClient
from app.adapters.open_prices import OpenPricesClient, OpenPricesServiceError
from app.adapters.product_repository import ProductRepository
from app.config import Settings
from app.domain.barcode import InvalidBarcodeError, normalize_barcode
from app.domain.product import Product
from app.domain.scoring import (
    analyze_sustainability,
    generic_environmental_factor,
)
from app.http.errors import ApiError
from app.http.product_schemas import (
    BarcodeLookupRequest,
    ProductCollectionResponse,
    ProductCompletionRequest,
    ProductResponse,
    SustainabilityAnalysisResponse,
)

SessionDependency = Callable[[], Iterator[Session]]


def create_product_router(
    get_session: SessionDependency,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/products", tags=["products"])
    open_food_facts = OpenFoodFactsClient(
        base_url=settings.open_food_facts_base_url,
        timeout_seconds=settings.external_api_timeout_seconds,
        user_agent=settings.external_api_user_agent,
    )
    open_prices = OpenPricesClient(
        base_url=settings.open_prices_base_url,
        timeout_seconds=settings.external_api_timeout_seconds,
        user_agent=settings.external_api_user_agent,
    )

    @router.get("", response_model=ProductCollectionResponse)
    def search_products(
        session: Annotated[Session, Depends(get_session)],
        query: Annotated[str, Query(max_length=120)] = "",
    ) -> ProductCollectionResponse:
        products = ProductRepository(session).search_products(query)
        return ProductCollectionResponse(
            items=[ProductResponse.from_product(product) for product in products]
        )

    @router.post("/barcode-lookup", response_model=ProductResponse)
    def lookup_barcode(
        request: BarcodeLookupRequest,
        session: Annotated[Session, Depends(get_session)],
    ) -> ProductResponse:
        try:
            barcode = normalize_barcode(request.barcode)
        except InvalidBarcodeError as error:
            raise ApiError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="INVALID_BARCODE",
                message=str(error),
            ) from error
        repository = ProductRepository(session)
        existing_product = repository.find_by_barcode(barcode)
        if existing_product:
            enriched_product = _enrich_with_price(existing_product, open_prices)
            if enriched_product != existing_product:
                enriched_product = repository.save_product(enriched_product)
            return ProductResponse.from_product(enriched_product)
        try:
            external_product = open_food_facts.find_product(
                barcode,
                request.barcode.strip(),
            )
        except ExternalServiceError as error:
            raise ApiError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="EXTERNAL_SERVICE_UNAVAILABLE",
                message="No fue posible consultar el producto en este momento.",
                details={"provider": "open_food_facts"},
            ) from error
        if external_product is None:
            raise ApiError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="PRODUCT_NOT_FOUND",
                message="No encontramos un producto con ese código de barras.",
            )
        enriched_product = _enrich_with_price(external_product, open_prices)
        return ProductResponse.from_product(repository.save_product(enriched_product))

    @router.get("/{product_id}/analysis", response_model=SustainabilityAnalysisResponse)
    def analyze_product(
        product_id: str,
        session: Annotated[Session, Depends(get_session)],
    ) -> SustainabilityAnalysisResponse:
        repository = ProductRepository(session)
        product = repository.find_product(product_id)
        if product is None:
            raise ApiError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="PRODUCT_NOT_FOUND",
                message="No encontramos el producto solicitado.",
            )
        factor = repository.find_environmental_factor(product.category)
        if factor is None:
            factors = repository.list_environmental_factors()
            if not factors:
                raise ApiError(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="ENVIRONMENTAL_DATA_UNAVAILABLE",
                    message="No hay factores ambientales disponibles.",
                )
            factor = generic_environmental_factor(factors)
        category_products = repository.list_by_category(product.category)
        analysis = analyze_sustainability(product, category_products, factor)
        return SustainabilityAnalysisResponse(
            product=ProductResponse.from_product(product),
            total_score=round(analysis.total_score, 1),
            economic_score=round(analysis.economic_score, 1),
            environmental_score=round(analysis.environmental_score, 1),
            social_score=round(analysis.social_score, 1),
            subcomponents={
                key: round(value, 1) for key, value in analysis.subcomponents.items()
            },
            reasons=list(analysis.reasons),
            data_sources=list(analysis.data_sources),
            confidence=analysis.confidence,
            co2e_kg=(
                round(analysis.co2e_kg, 3) if analysis.co2e_kg is not None else None
            ),
            price_per_100g=(
                round(analysis.price_per_100g, 1)
                if analysis.price_per_100g is not None
                else None
            ),
        )

    @router.patch("/{product_id}", response_model=ProductResponse)
    def complete_product(
        product_id: str,
        request: ProductCompletionRequest,
        session: Annotated[Session, Depends(get_session)],
    ) -> ProductResponse:
        repository = ProductRepository(session)
        product = repository.find_product(product_id)
        if product is None:
            raise ApiError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="PRODUCT_NOT_FOUND",
                message="No encontramos el producto solicitado.",
            )
        if product.external_provider == "local" or product.is_complete:
            raise ApiError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="PRODUCT_NOT_EDITABLE",
                message="Solo puedes completar productos externos con datos pendientes.",
            )
        updated_product = replace(
            product,
            price_clp=request.price_clp or product.price_clp,
            package_grams=request.package_grams or product.package_grams,
            category=request.category or product.category,
            updated_at=datetime.now(UTC),
        )
        return ProductResponse.from_product(repository.save_product(updated_product))

    return router


def _enrich_with_price(
    product: Product,
    open_prices: OpenPricesClient,
) -> Product:
    if product.external_provider == "local" or product.price_clp is not None:
        return product
    try:
        price_clp = open_prices.find_latest_clp_price(product.barcode_raw)
    except OpenPricesServiceError:
        return product
    if price_clp is None:
        return product
    providers = product.external_provider.split("+")
    if "open_prices" not in providers:
        providers.append("open_prices")
    return replace(
        product,
        price_clp=price_clp,
        external_provider="+".join(providers),
        updated_at=datetime.now(UTC),
    )
