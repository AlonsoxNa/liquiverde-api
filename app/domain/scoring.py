from dataclasses import dataclass
from statistics import median

from app.domain.product import EnvironmentalFactor, Product

RECOGNIZED_CERTIFICATIONS = {"fairtrade", "rainforest_alliance", "utz"}


@dataclass(frozen=True)
class SustainabilityAnalysis:
    total_score: float
    economic_score: float
    environmental_score: float
    social_score: float
    subcomponents: dict[str, float]
    reasons: tuple[str, ...]
    data_sources: tuple[str, ...]
    confidence: str
    co2e_kg: float | None
    price_per_100g: float | None


def analyze_sustainability(
    product: Product,
    category_products: list[Product],
    environmental_factor: EnvironmentalFactor,
) -> SustainabilityAnalysis:
    price_per_100g = _price_per_100g(product)
    comparable_prices = [
        price
        for candidate in category_products
        if (price := _price_per_100g(candidate)) is not None
    ]
    economic_score = _inverse_min_max(price_per_100g, comparable_prices)

    co2e_kg = _product_co2e(product, environmental_factor)
    comparable_footprints = [
        footprint
        for candidate in category_products
        if (footprint := _product_co2e(candidate, environmental_factor)) is not None
    ]
    climate_score = _inverse_min_max(co2e_kg, comparable_footprints)
    local_origin_score = _boolean_score(
        None if product.origin is None else product.origin == "local"
    )
    recyclable_packaging_score = _boolean_score(product.recyclable)
    environmental_score = (
        0.70 * climate_score
        + 0.15 * local_origin_score
        + 0.15 * recyclable_packaging_score
    )
    social_score = _social_score(product)
    total_score = (
        0.40 * economic_score + 0.40 * environmental_score + 0.20 * social_score
    )
    reasons = _build_reasons(
        product,
        economic_score,
        climate_score,
        social_score,
    )
    return SustainabilityAnalysis(
        total_score=total_score,
        economic_score=economic_score,
        environmental_score=environmental_score,
        social_score=social_score,
        subcomponents={
            "climate": climate_score,
            "local_origin": local_origin_score,
            "recyclable_packaging": recyclable_packaging_score,
        },
        reasons=reasons,
        data_sources=tuple(
            dict.fromkeys(
                [*product.external_provider.split("+"), environmental_factor.source]
            )
        ),
        confidence=_confidence(product, environmental_factor),
        co2e_kg=co2e_kg,
        price_per_100g=price_per_100g,
    )


def generic_environmental_factor(
    factors: list[EnvironmentalFactor],
) -> EnvironmentalFactor:
    available_values = [factor.co2e_kg_per_kg for factor in factors]
    reference = factors[0]
    return EnvironmentalFactor(
        category="other",
        co2e_kg_per_kg=median(available_values),
        source="AGRIBALYSE",
        source_version=reference.source_version,
        confidence="low",
        updated_at=max(factor.updated_at for factor in factors),
    )


def _price_per_100g(product: Product) -> float | None:
    if not product.price_clp or not product.package_grams:
        return None
    return product.price_clp * 100 / product.package_grams


def _product_co2e(
    product: Product,
    environmental_factor: EnvironmentalFactor,
) -> float | None:
    if not product.package_grams:
        return None
    return environmental_factor.co2e_kg_per_kg * product.package_grams / 1000


def _inverse_min_max(value: float | None, values: list[float]) -> float:
    if value is None or not values:
        return 50.0
    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return 50.0
    return 100 * (maximum - value) / (maximum - minimum)


def _boolean_score(value: bool | None) -> float:
    if value is None:
        return 50.0
    return 100.0 if value else 0.0


def _social_score(product: Product) -> float:
    if RECOGNIZED_CERTIFICATIONS.intersection(product.certifications):
        return 100.0
    if product.social_indicator == "responsible_policy":
        return 75.0
    return 50.0


def _build_reasons(
    product: Product,
    economic_score: float,
    climate_score: float,
    social_score: float,
) -> tuple[str, ...]:
    reasons = [
        f"Su posición relativa de precio aporta {economic_score:.1f} puntos.",
        f"La huella climática de su presentación aporta {climate_score:.1f} puntos.",
    ]
    if product.origin is None:
        reasons.append("No hay información de origen; se aplica un valor neutral.")
    elif product.origin == "local":
        reasons.append("El origen local mejora el componente ambiental.")
    else:
        reasons.append("El origen importado no suma puntos por proximidad.")
    if product.recyclable is None:
        reasons.append(
            "No hay información de reciclabilidad; se aplica un valor neutral."
        )
    elif product.recyclable:
        reasons.append("El empaque reciclable mejora el componente ambiental.")
    else:
        reasons.append("El empaque no reciclable no suma puntos de reciclabilidad.")
    if social_score == 100:
        reasons.append("Cuenta con una certificación social reconocida.")
    elif social_score == 75:
        reasons.append("Cuenta con un indicador responsable documentado.")
    else:
        reasons.append("No hay información social; se aplica un valor neutral.")
    return tuple(reasons)


def _confidence(
    product: Product,
    environmental_factor: EnvironmentalFactor,
) -> str:
    if not product.is_complete or product.category == "other":
        return "low"
    if (
        product.origin is None
        or product.recyclable is None
        or environmental_factor.confidence != "high"
    ):
        return "medium"
    return "high"
