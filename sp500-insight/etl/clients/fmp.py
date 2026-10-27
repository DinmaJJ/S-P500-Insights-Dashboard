"""Financial Modeling Prep client (free tier aware)."""

from __future__ import annotations
import os
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY", "")
        if not self.api_key:
            raise ValueError("FMP_API_KEY is required")
        self.client = httpx.Client(timeout=30.0)

    def _get(self, path: str, params: dict | None = None) -> Any:
        params = params or {}
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}{path}"
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_sp500_constituents(self) -> list[dict]:
        """Current S&P 500 list."""
        return self._get("/sp500_constituent")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_company_profile(self, symbol: str) -> list[dict]:
        return self._get(f"/profile/{symbol}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_key_metrics(self, symbol: str, limit: int = 5) -> list[dict]:
        return self._get(f"/key-metrics/{symbol}", {"limit": limit})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_ratios(self, symbol: str, limit: int = 5) -> list[dict]:
        return self._get(f"/ratios/{symbol}", {"limit": limit})

    def close(self):
        self.client.close()
