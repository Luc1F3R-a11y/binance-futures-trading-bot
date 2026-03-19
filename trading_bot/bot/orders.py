"""
Order placement logic for Binance USDT-M Futures.

This module sits between the raw HTTP client (client.py) and the CLI.
It:
  - Translates validated parameters into Binance API payloads.
  - Normalises the API response into a clean OrderResult dataclass.
  - Logs a human-readable summary of every placed order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient
from .logging_config import get_logger
from .validators import validate_all, ValidationError

logger = get_logger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    """Normalised representation of a Binance order response."""

    order_id: int
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str          # limit price (0 for MARKET)
    time_in_force: str
    raw: Dict[str, Any] = field(repr=False)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "OrderResult":
        """Build an OrderResult from the raw Binance API dict."""
        return cls(
            order_id=data.get("orderId", 0),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            price=data.get("price", "0"),
            time_in_force=data.get("timeInForce", ""),
            raw=data,
        )

    def to_display_dict(self) -> Dict[str, str]:
        """Return a dict suitable for pretty-printing in the CLI."""
        return {
            "Order ID":       str(self.order_id),
            "Client ID":      self.client_order_id,
            "Symbol":         self.symbol,
            "Side":           self.side,
            "Type":           self.order_type,
            "Status":         self.status,
            "Original Qty":   self.orig_qty,
            "Executed Qty":   self.executed_qty,
            "Avg Fill Price": self.avg_price,
            "Limit Price":    self.price,
            "Time In Force":  self.time_in_force,
        }


# ── Order builders ────────────────────────────────────────────────────────────

def _build_market_order(
    symbol: str,
    side: str,
    quantity: Decimal,
) -> Dict[str, Any]:
    return {
        "symbol":   symbol,
        "side":     side,
        "type":     "MARKET",
        "quantity": str(quantity),
    }


def _build_limit_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    return {
        "symbol":      symbol,
        "side":        side,
        "type":        "LIMIT",
        "quantity":    str(quantity),
        "price":       str(price),
        "timeInForce": time_in_force,
    }


def _build_stop_market_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> Dict[str, Any]:
    return {
        "symbol":    symbol,
        "side":      side,
        "type":      "STOP_MARKET",
        "quantity":  str(quantity),
        "stopPrice": str(stop_price),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def place_order(
    client: BinanceFuturesClient,
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float | Decimal,
    price: Optional[str | float | Decimal] = None,
    stop_price: Optional[str | float | Decimal] = None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Validate parameters, build the appropriate payload, and place the order.

    Parameters:
        client:         Authenticated BinanceFuturesClient instance.
        symbol:         Trading pair (e.g. "BTCUSDT").
        side:           "BUY" or "SELL".
        order_type:     "MARKET", "LIMIT", or "STOP_MARKET".
        quantity:       Order quantity (positive number).
        price:          Limit price (required for LIMIT orders).
        stop_price:     Trigger price (required for STOP_MARKET orders).
        time_in_force:  "GTC" | "IOC" | "FOK" (applies to LIMIT orders).

    Returns:
        OrderResult dataclass with normalised fields.

    Raises:
        ValidationError:    On invalid input parameters.
        BinanceAPIError:    On API-level errors.
        BinanceNetworkError: On network failures.
    """

    # ── 1. Validate ───────────────────────────────────────────────────────────
    params = validate_all(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    logger.info(
        "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        params["symbol"],
        params["side"],
        params["order_type"],
        params["quantity"],
        params["price"],
        params["stop_price"],
    )

    # ── 2. Build payload ──────────────────────────────────────────────────────
    ot = params["order_type"]

    if ot == "MARKET":
        payload = _build_market_order(
            params["symbol"], params["side"], params["quantity"]
        )
    elif ot == "LIMIT":
        payload = _build_limit_order(
            params["symbol"],
            params["side"],
            params["quantity"],
            params["price"],
            time_in_force=time_in_force,
        )
    elif ot == "STOP_MARKET":
        payload = _build_stop_market_order(
            params["symbol"],
            params["side"],
            params["quantity"],
            params["stop_price"],
        )
    else:
        # Should be unreachable — validators guard this
        raise ValidationError(f"Unsupported order type: {ot}")

    logger.debug("API payload: %s", json.dumps(payload))

    # ── 3. Place order ────────────────────────────────────────────────────────
    response = client.place_order(**payload)

    # ── 4. Normalise & return ─────────────────────────────────────────────────
    result = OrderResult.from_api_response(response)
    logger.info(
        "Order placed successfully: orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result
