"""Tiingo client for high-quality historical OHLCV."""

from __future__ import annotations
import os
from datetime import date
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class TiingoClient:
    BASE_URL = "https://api.tiingo.com"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TIINGO_API_KEY", "")
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY is required")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }
        self.client = httpx.Client(timeout=60.0, headers=self.headers)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_daily_prices(
        self,
        symbol: str,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[dict]:
        """Fetch daily OHLCV (adjusted) for a symbol."""
        params: dict[str, Any] = {}
        if start_date:
            params["startDate"] = str(start_date)
        if end_date:
            params["endDate"] = str(end_date)

        url = f"{self.BASE_URL}/tiingo/daily/{symbol}/prices"
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self.client.close()
