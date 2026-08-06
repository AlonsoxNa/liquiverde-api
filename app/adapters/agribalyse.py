import logging
from statistics import median
from time import monotonic
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)

CATEGORY_QUERIES = {
    "rice": "riz blanc cru",
    "pasta": "pâtes alimentaires",
    "milk_and_plant_drinks": "lait demi-écrémé",
    "legumes": "lentille sèche",
    "coffee": "café moulu",
    "chocolate": "chocolat noir",
}


class AgribalyseServiceError(RuntimeError):
    pass


class AgribalyseClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        user_agent: str,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch_category_factor(self, category: str) -> float:
        query = CATEGORY_QUERIES[category]
        started_at = monotonic()
        try:
            response = httpx.get(
                f"{self.base_url}/lines",
                params={"size": 50, "qs": query},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            results = response.json().get("results") or []
            values = self._extract_climate_values(results)
            if not values:
                raise AgribalyseServiceError(
                    f"AGRIBALYSE no devolvió valores para {category}."
                )
            self._log_request(category, started_at, response.status_code, "success")
            return median(values)
        except AgribalyseServiceError:
            self._log_request(category, started_at, 0, "empty")
            raise
        except (httpx.HTTPError, ValueError, TypeError) as error:
            self._log_request(category, started_at, 0, "transport_error")
            raise AgribalyseServiceError(
                f"No fue posible actualizar la categoría {category}."
            ) from error

    @staticmethod
    def _extract_climate_values(results: list[dict[str, Any]]) -> list[float]:
        return [
            float(value)
            for result in results
            if isinstance((value := result.get("Changement_climatique")), int | float)
            and value > 0
        ]

    @staticmethod
    def _log_request(
        category: str,
        started_at: float,
        status_code: int,
        status: str,
    ) -> None:
        LOGGER.info(
            "external_provider=agribalyse category=%s status=%s status_code=%s duration_ms=%.1f",
            category,
            status,
            status_code,
            (monotonic() - started_at) * 1000,
        )
