#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet trading bot.

Usage examples:
  # Market BUY
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 99000

  # Stop-Market BUY (bonus order type)
  python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

  # Load credentials from environment variables (recommended)
  export BINANCE_API_KEY="your_key"
  export BINANCE_API_SECRET="your_secret"
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from typing import Optional

from bot.client import BinanceAPIError, BinanceNetworkError, BinanceFuturesClient
from bot.logging_config import setup_logging, LOG_FILE
from bot.orders import place_order
from bot.validators import ValidationError

# ── ANSI colours (disabled on non-TTY terminals) ──────────────────────────────
_USE_COLOUR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def green(t: str) -> str:  return _c("32;1", t)
def red(t: str) -> str:    return _c("31;1", t)
def cyan(t: str) -> str:   return _c("36;1", t)
def yellow(t: str) -> str: return _c("33;1", t)
def bold(t: str) -> str:   return _c("1", t)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    width = 54
    print(f"\n{cyan('─' * width)}")
    print(f"  {bold(title)}")
    print(f"{cyan('─' * width)}")


def _kv(key: str, value: str, width: int = 18) -> str:
    return f"  {bold(key + ':'):<{width + 7}} {value}"


def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
) -> None:
    _section("ORDER REQUEST")
    print(_kv("Symbol",     symbol))
    print(_kv("Side",       (green if side == "BUY" else red)(side)))
    print(_kv("Type",       order_type))
    print(_kv("Quantity",   quantity))
    if price:
        print(_kv("Limit Price", price))
    if stop_price:
        print(_kv("Stop Price", stop_price))


def _print_order_result(result) -> None:
    _section("ORDER RESPONSE")
    display = result.to_display_dict()
    for key, value in display.items():
        if not value or value in ("0", "0.00000000", ""):
            continue
        if key == "Side":
            value = (green if value == "BUY" else red)(value)
        elif key == "Status":
            value = green(value) if value == "FILLED" else yellow(value)
        print(_kv(key, value))


def _print_success() -> None:
    print(f"\n  {green('✓  Order placed successfully!')}")
    print(f"  Log file: {LOG_FILE}\n")


def _print_failure(message: str) -> None:
    print(f"\n  {red('✗  Order failed:')}")
    print(f"  {red(message)}\n")


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Binance USDT-M Futures Testnet — Trading Bot CLI
            ─────────────────────────────────────────────────
            Place MARKET, LIMIT, or STOP_MARKET orders on the
            Binance Futures Testnet via the REST API.
            """
        ),
        epilog=textwrap.dedent(
            """\
            Examples:
              python cli.py --symbol BTCUSDT --side BUY  --type MARKET     --quantity 0.001
              python cli.py --symbol BTCUSDT --side SELL --type LIMIT       --quantity 0.001 --price 99000
              python cli.py --symbol BTCUSDT --side BUY  --type STOP_MARKET --quantity 0.001 --stop-price 95000

            Credentials (pick one):
              1. Flags     : --api-key KEY --api-secret SECRET
              2. Env vars  : BINANCE_API_KEY / BINANCE_API_SECRET  (recommended)
            """
        ),
    )

    # ── Credentials ────────────────────────────────────────────────────────
    creds = parser.add_argument_group("credentials")
    creds.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY"),
        metavar="KEY",
        help="Binance Testnet API key (or set BINANCE_API_KEY env var).",
    )
    creds.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET"),
        metavar="SECRET",
        help="Binance Testnet API secret (or set BINANCE_API_SECRET env var).",
    )

    # ── Order parameters ────────────────────────────────────────────────────
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT.",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        metavar="SIDE",
        help="BUY or SELL.",
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
        metavar="TYPE",
        help="MARKET | LIMIT | STOP_MARKET.",
    )
    order.add_argument(
        "--quantity",
        required=True,
        metavar="QTY",
        help="Order quantity (e.g. 0.001).",
    )
    order.add_argument(
        "--price",
        default=None,
        metavar="PRICE",
        help="Limit price — required for LIMIT orders.",
    )
    order.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price — required for STOP_MARKET orders.",
    )
    order.add_argument(
        "--tif",
        dest="time_in_force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC).",
    )

    # ── Misc ────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity (default: INFO).",
    )
    parser.add_argument(
        "--no-colour",
        action="store_true",
        help="Disable ANSI colour output.",
    )

    return parser


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Disable colour if requested
    global _USE_COLOUR
    if args.no_colour:
        _USE_COLOUR = False

    # Set up logging first
    setup_logging(log_level=args.log_level, log_to_console=True)

    # ── Credential check ────────────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        parser.error(
            "API credentials are required.\n"
            "  Pass --api-key / --api-secret, or set the "
            "BINANCE_API_KEY / BINANCE_API_SECRET environment variables."
        )

    # ── Print request summary ───────────────────────────────────────────────
    _print_request_summary(
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
    )

    # ── Place the order ─────────────────────────────────────────────────────
    try:
        client = BinanceFuturesClient(
            api_key=args.api_key,
            api_secret=args.api_secret,
        )

        result = place_order(
            client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )

    except ValidationError as exc:
        _print_failure(f"Validation error: {exc}")
        return 1

    except BinanceAPIError as exc:
        _print_failure(f"Binance API error (code {exc.code}): {exc}")
        return 1

    except BinanceNetworkError as exc:
        _print_failure(f"Network error: {exc}")
        return 1

    except Exception as exc:  # noqa: BLE001
        _print_failure(f"Unexpected error: {exc}")
        return 1

    # ── Print result ────────────────────────────────────────────────────────
    _print_order_result(result)
    _print_success()
    return 0


if __name__ == "__main__":
    sys.exit(main())
