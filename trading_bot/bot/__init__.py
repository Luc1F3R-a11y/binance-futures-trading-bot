"""
Binance Futures Testnet Trading Bot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Package entry point — exposes the public API surface.
"""

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from .orders import place_order, OrderResult
from .validators import ValidationError

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "BinanceNetworkError",
    "place_order",
    "OrderResult",
    "ValidationError",
]
