import logging
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx

from app.domain.product import Product

LOGGER = logging.getLogger(__name__)

CATEGORY_TAGS = {
    "rice": {"en:rices", "en:rice"},
    "pasta": {"en:pastas", "en:pasta"},
    "milk_and_plant_drinks": {
        "en:milks",
        "en:milk",
        "en:plant-based-beverages",
        "en:plant-milks",
    },
    "legumes": {"en:legumes", "en:pulses", "en:dried-legumes"},
    "coffee": {"en:coffees", "en:coffee"},
    "chocolate": {"en:chocolates", "en:chocolate"},
}

CERTIFICATION_TAGS = {
    "en:fairtrade-international": "fairtrade",
    "en:fairtrade": "fairtrade",
    "en:rainforest-alliance": "rainforest_alliance",
    "en:utz-certified": "utz",
}


class ExternalServiceError(RuntimeError):
    pass


class OpenFoodFactsClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        user_agent: str,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def find_product(self, barcode: str, barcode_raw: str) -> Product | None:
        started_at = monotonic()
        try:
            response = httpx.get(
                f"{self.base_url}/product/{barcode}.json",
                params={"fields": self._requested_fields()},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_seconds,
            )
            if response.status_code == 404:
                self._log_request(started_at, response.status_code, "not_found")
                return None
            if response.status_code in {429, 500, 502, 503, 504}:
                self._log_request(started_at, response.status_code, "unavailable")
                raise ExternalServiceError("Open Food Facts no está disponible.")
            response.raise_for_status()
            product_data = response.json().get("product")
            if not product_data:
                self._log_request(started_at, response.status_code, "not_found")
                return None
            product = self._create_product(barcode, barcode_raw, product_data)
            self._log_request(started_at, response.status_code, "success")
            return product
        except (httpx.HTTPError, ValueError, TypeError) as error:
            self._log_request(started_at, 0, "transport_error")
            raise ExternalServiceError("Open Food Facts no está disponible.") from error

    @staticmethod
    def _requested_fields() -> str:
        return ",".join(
            [
                "code",
                "product_name",
                "generic_name",
                "brands",
                "categories_tags",
                "countries_tags",
                "packaging_tags",
                "labels_tags",
                "product_quantity",
                "product_quantity_unit",
                "quantity",
            ]
        )

    def _create_product(
        self,
        barcode: str,
        barcode_raw: str,
        data: dict[str, Any],
    ) -> Product:
        category_tags = set(data.get("categories_tags") or [])
        country_tags = set(data.get("countries_tags") or [])
        packaging_tags = tuple(data.get("packaging_tags") or [])
        label_tags = tuple(data.get("labels_tags") or [])
        return Product(
            id=f"off-{barcode}",
            barcode=barcode,
            barcode_raw=barcode_raw,
            name=(
                data.get("product_name")
                or data.get("generic_name")
                or f"Producto {barcode}"
            ).strip(),
            brand=(data.get("brands") or "Sin marca").split(",")[0].strip(),
            category=self._map_category(category_tags),
            price_clp=None,
            package_grams=self._extract_weight(data),
            origin=self._map_origin(country_tags),
            packaging_type=packaging_tags[0] if packaging_tags else None,
            recyclable=self._map_recyclability(packaging_tags),
            certifications=self._map_certifications(label_tags),
            social_indicator=None,
            external_provider="open_food_facts",
            external_id=str(data.get("code") or barcode),
            updated_at=datetime.now(UTC),
        )

    @staticmethod
    def _map_category(tags: set[str]) -> str:
        for category, candidates in CATEGORY_TAGS.items():
            if tags.intersection(candidates):
                return category
        return "other"

    @staticmethod
    def _map_origin(tags: set[str]) -> str | None:
        if not tags:
            return None
        return "local" if "en:chile" in tags else "imported"

    @staticmethod
    def _map_recyclability(tags: tuple[str, ...]) -> bool | None:
        if not tags:
            return None
        return any("recycl" in tag for tag in tags)

    @staticmethod
    def _map_certifications(tags: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    certification
                    for tag, certification in CERTIFICATION_TAGS.items()
                    if tag in tags
                }
            )
        )

    @staticmethod
    def _extract_weight(data: dict[str, Any]) -> float | None:
        quantity = data.get("product_quantity")
        unit = str(data.get("product_quantity_unit") or "g").lower()
        if not isinstance(quantity, int | float) or quantity <= 0:
            return None
        if unit in {"kg", "kilogram", "kilograms"}:
            return float(quantity) * 1000
        if unit in {"ml", "milliliter", "milliliters"}:
            return float(quantity)
        return float(quantity)

    @staticmethod
    def _log_request(started_at: float, status_code: int, status: str) -> None:
        LOGGER.info(
            "external_provider=open_food_facts status=%s status_code=%s duration_ms=%.1f",
            status,
            status_code,
            (monotonic() - started_at) * 1000,
        )
