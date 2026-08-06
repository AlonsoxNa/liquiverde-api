import logging
from time import monotonic
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


class OpenPricesServiceError(RuntimeError):
    pass


class OpenPricesClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        user_agent: str,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def find_latest_clp_price(self, barcode: str) -> int | None:
        started_at = monotonic()
        try:
            response = httpx.get(
                f"{self.base_url}/prices",
                params={
                    "product_code": barcode,
                    "currency": "CLP",
                    "size": 20,
                    "order_by": "-date",
                },
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            price = self._extract_latest_chilean_price(
                response.json().get("items") or []
            )
            self._log_request(
                started_at,
                response.status_code,
                "success" if price is not None else "not_found",
            )
            return price
        except (httpx.HTTPError, ValueError, TypeError) as error:
            self._log_request(started_at, 0, "transport_error")
            raise OpenPricesServiceError(
                "Open Prices no está disponible."
            ) from error

    @staticmethod
    def _extract_latest_chilean_price(items: list[dict[str, Any]]) -> int | None:
        for item in items:
            location = item.get("location") or {}
            price = item.get("price")
            if (
                item.get("currency") == "CLP"
                and location.get("osm_address_country_code") == "CL"
                and isinstance(price, int | float)
                and not isinstance(price, bool)
                and price > 0
            ):
                return round(price)
        return None

    @staticmethod
    def _log_request(started_at: float, status_code: int, status: str) -> None:
        LOGGER.info(
            "external_provider=open_prices status=%s status_code=%s duration_ms=%.1f",
            status,
            status_code,
            (monotonic() - started_at) * 1000,
        )
