from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.adapters.product_repository import ProductRepository
from app.application.shopping_list_optimizer import (
    ShoppingListValidationError,
    ShoppingNeedInput,
    optimize_shopping_list,
)
from app.http.errors import ApiError
from app.http.product_schemas import ProductResponse
from app.http.shopping_list_schemas import (
    OptimizationSummaryResponse,
    OptimizedSelectionResponse,
    OptimizeShoppingListRequest,
    OptimizeShoppingListResponse,
)

SessionDependency = Callable[[], Iterator[Session]]


def create_shopping_list_router(get_session: SessionDependency) -> APIRouter:
    router = APIRouter(prefix="/api/v1/shopping-lists", tags=["shopping-lists"])

    @router.post("/optimize", response_model=OptimizeShoppingListResponse)
    def optimize(
        request: OptimizeShoppingListRequest,
        session: Annotated[Session, Depends(get_session)],
    ) -> OptimizeShoppingListResponse:
        repository = ProductRepository(session)
        try:
            outcome = optimize_shopping_list(
                repository=repository,
                budget_clp=request.budget_clp,
                needs=tuple(
                    ShoppingNeedInput(
                        reference_product_id=need.reference_product_id,
                        quantity=need.quantity,
                    )
                    for need in request.needs
                ),
                economic_weight=request.preferences.economic,
                environmental_weight=request.preferences.environmental,
                social_weight=request.preferences.social,
            )
        except ShoppingListValidationError as error:
            raise ApiError(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                    if error.code == "PRODUCT_NOT_FOUND"
                    else status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                code=error.code,
                message=error.message,
                details=error.details,
            ) from error
        reference_cost = sum(
            selection.need.reference.product.price_clp * selection.need.quantity
            for selection in outcome.selections
        )
        reference_co2e = sum(
            selection.need.reference.unit_co2e_kg * selection.need.quantity
            for selection in outcome.selections
        )
        savings = reference_cost - outcome.optimized_cost
        avoided_co2e = reference_co2e - outcome.optimized_co2e_kg
        return OptimizeShoppingListResponse(
            selections=[
                _create_selection_response(selection)
                for selection in outcome.selections
            ],
            summary=OptimizationSummaryResponse(
                budget_clp=request.budget_clp,
                reference_cost_clp=reference_cost,
                optimized_cost_clp=outcome.optimized_cost,
                savings_clp=savings,
                savings_percentage=round(savings * 100 / reference_cost, 1),
                reference_co2e_kg=round(reference_co2e, 3),
                optimized_co2e_kg=round(outcome.optimized_co2e_kg, 3),
                avoided_co2e_kg=round(avoided_co2e, 3),
                aggregate_utility=round(outcome.aggregate_utility, 1),
                aggregate_score=round(outcome.aggregate_score, 1),
                uncovered_categories=list(outcome.uncovered_categories),
            ),
        )

    return router


def _create_selection_response(selection) -> OptimizedSelectionResponse:
    candidate = selection.candidate
    if candidate is None:
        return OptimizedSelectionResponse(
            category=selection.need.category,
            quantity=selection.need.quantity,
            reference_product=ProductResponse.from_product(
                selection.need.reference.product
            ),
            selected_product=None,
            cost_clp=0,
            score=None,
            co2e_kg=0,
            reason="El presupuesto no permite cubrir esta categoría.",
        )
    conserved = candidate.product.id == selection.need.reference.product.id
    return OptimizedSelectionResponse(
        category=selection.need.category,
        quantity=selection.need.quantity,
        reference_product=ProductResponse.from_product(
            selection.need.reference.product
        ),
        selected_product=ProductResponse.from_product(candidate.product),
        cost_clp=candidate.product.price_clp * selection.need.quantity,
        score=round(candidate.total_score, 1),
        co2e_kg=round(candidate.unit_co2e_kg * selection.need.quantity, 3),
        reason=(
            "Se conserva la referencia según tus prioridades y presupuesto."
            if conserved
            else "Se sustituye para mejorar la utilidad respetando el presupuesto."
        ),
    )
