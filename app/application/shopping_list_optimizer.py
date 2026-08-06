from dataclasses import dataclass

from app.adapters.product_repository import ProductRepository
from app.domain.optimization import (
    NeedOptions,
    OptimizationCandidate,
    OptimizationOutcome,
    optimize_needs,
)
from app.domain.scoring import analyze_sustainability


@dataclass(frozen=True)
class ShoppingNeedInput:
    reference_product_id: str
    quantity: int


class ShoppingListValidationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def optimize_shopping_list(
    repository: ProductRepository,
    budget_clp: int,
    needs: tuple[ShoppingNeedInput, ...],
    economic_weight: float,
    environmental_weight: float,
    social_weight: float,
) -> OptimizationOutcome:
    weight_sum = economic_weight + environmental_weight + social_weight
    normalized_weights = (
        economic_weight / weight_sum,
        environmental_weight / weight_sum,
        social_weight / weight_sum,
    )
    options: list[NeedOptions] = []
    used_categories: set[str] = set()
    for need in needs:
        reference = repository.find_product(need.reference_product_id)
        if reference is None:
            raise ShoppingListValidationError(
                "PRODUCT_NOT_FOUND",
                "No encontramos uno de los productos de referencia.",
                {"product_id": need.reference_product_id},
            )
        if not reference.is_complete:
            raise ShoppingListValidationError(
                "INCOMPLETE_PRODUCT",
                "Todos los productos de referencia deben estar completos.",
                {"product_id": reference.id},
            )
        if reference.category in used_categories:
            raise ShoppingListValidationError(
                "DUPLICATE_CATEGORY",
                "La lista solo puede contener una necesidad por categoría.",
                {"category": reference.category},
            )
        used_categories.add(reference.category)
        factor = repository.find_environmental_factor(reference.category)
        if factor is None:
            raise ShoppingListValidationError(
                "ENVIRONMENTAL_DATA_UNAVAILABLE",
                "No hay un factor ambiental para la categoría solicitada.",
                {"category": reference.category},
            )
        category_products = [
            product
            for product in repository.list_by_category(reference.category)
            if product.is_complete
        ]
        candidates = tuple(
            _build_candidate(
                product,
                category_products,
                factor,
                normalized_weights,
            )
            for product in category_products
        )
        reference_candidate = next(
            candidate
            for candidate in candidates
            if candidate.product.id == reference.id
        )
        options.append(
            NeedOptions(
                category=reference.category,
                quantity=need.quantity,
                reference=reference_candidate,
                candidates=candidates,
            )
        )
    return optimize_needs(tuple(options), budget_clp)


def _build_candidate(
    product,
    category_products,
    factor,
    normalized_weights: tuple[float, float, float],
) -> OptimizationCandidate:
    analysis = analyze_sustainability(product, category_products, factor)
    economic_weight, environmental_weight, social_weight = normalized_weights
    utility = (
        economic_weight * analysis.economic_score
        + environmental_weight * analysis.environmental_score
        + social_weight * analysis.social_score
    )
    return OptimizationCandidate(
        product=product,
        total_score=analysis.total_score,
        utility=utility,
        unit_co2e_kg=analysis.co2e_kg or 0,
    )
