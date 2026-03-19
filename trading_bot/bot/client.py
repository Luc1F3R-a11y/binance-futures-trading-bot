"""
Low-level Binance Futures Testnet REST client.

Responsibilities:
- Sign requests with HMAC-SHA256.
- Manage the HTTP session (keep-alive, timeouts, retries).
- Log every outbound request and inbound response.
- Raise typed exceptions for API-level and network-level errors.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger

logger = get_logger(__name__)

# ── Testnet base URL (USDT-M Futures) ────────────────────────────────────────
TESTNET_BASE_URL = "https://testnet.binancefuture.com"

# ── Timeouts & retry policy ──────────────────────────────────────────────────
REQUEST_TIMEOUT = 10  # seconds
_RETRY_POLICY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "DELETE"],
)


# ── Custom exceptions ─────────────────────────────────────────────────────────

class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-OK status or an error payload."""

    def __init__(self, message: str, code: int = 0, http_status: int = 0):
        super().__init__(message)
        self.code = code            # Binance error code (e.g. -1121)
        self.http_status = http_status


class BinanceNetworkError(Exception):
    """Raised on network-level failures (timeouts, connection errors)."""


# ── Client ───────────────────────────────────────────────────────────────────

class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Parameters:
        api_key:    Testnet API key.
        api_secret: Testnet API secret.
        base_url:   Override the default testnet base URL (useful for tests).
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")

        self._session = self._build_session()
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self._base_url)

    # ── Session ──────────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY_POLICY)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        return session

    # ── Signing ───────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append timestamp + HMAC-SHA256 signature to a parameter dict."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance Futures REST API.

        Args:
            method:   HTTP verb ("GET", "POST", "DELETE").
            endpoint: Path, e.g. "/fapi/v1/order".
            params:   Query / body parameters.
            signed:   Whether to attach timestamp + signature.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            BinanceAPIError:     API returned an error payload or 4xx/5xx.
            BinanceNetworkError: Network-level failure.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"

        # Redact signature from log output
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.info("→ %s %s  params=%s", method, endpoint, log_params)

        try:
            if method == "GET":
                response = self._session.get(
                    url, params=params, timeout=REQUEST_TIMEOUT
                )
            elif method == "POST":
                response = self._session.post(
                    url, data=params, timeout=REQUEST_TIMEOUT
                )
            elif method == "DELETE":
                response = self._session.delete(
                    url, params=params, timeout=REQUEST_TIMEOUT
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(
                f"Request timed out after {REQUEST_TIMEOUT}s: {exc}"
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(
                f"Connection error while calling {endpoint}: {exc}"
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error: %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(str(exc)) from exc

        logger.info(
            "← %s %s  status=%d  body=%s",
            method,
            endpoint,
            response.status_code,
            response.text[:500],  # truncate large payloads in the log
        )

        # Parse JSON (Binance always returns JSON)
        try:
            data = response.json()
        except ValueError:
            raise BinanceAPIError(
                f"Non-JSON response from {endpoint}: {response.text[:200]}",
                http_status=response.status_code,
            )

        # Binance encodes errors as {"code": <negative_int>, "msg": "..."}
        if isinstance(data, dict) and data.get("code", 0) < 0:
            error_code = data["code"]
            error_msg = data.get("msg", "Unknown API error")
            logger.error(
                "Binance API error: code=%d  msg=%s", error_code, error_msg
            )
            raise BinanceAPIError(
                f"Binance API error {error_code}: {error_msg}",
                code=error_code,
                http_status=response.status_code,
            )

        if not response.ok:
            raise BinanceAPIError(
                f"HTTP {response.status_code} from {endpoint}: {response.text[:200]}",
                http_status=response.status_code,
            )

        return data

    # ── Public API methods ────────────────────────────────────────────────────

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info (symbols, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Place a new order.

        Keyword arguments are forwarded directly to POST /fapi/v1/order.
        See orders.py for the expected keys.
        """
        return self._request("POST", "/fapi/v1/order", params=dict(kwargs))

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by orderId."""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        """Retrieve all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query the status of a specific order."""
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol.upper(), "orderId": order_id},
        )
