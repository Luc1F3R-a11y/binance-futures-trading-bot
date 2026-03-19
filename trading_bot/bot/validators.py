"""
Input validation for order parameters.
All validation is pure — no side effects, no I/O.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}
SYMBOL_MAX_LENGTH = 20
MIN_POSITIVE = Decimal("0.00000001")


# ── Exceptions ────────────────────────────────────────────────────────────────

class ValidationError(ValueError):
    """Raised when order parameter validation fails."""


# ── Validators ────────────────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """
    Ensure symbol is a non-empty uppercase alphanumeric string.

    Returns:
        Normalised (uppercase, stripped) symbol.

    Raises:
        ValidationError: on any constraint violation.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol must be a non-empty string.")

    symbol = symbol.strip().upper()

    if not symbol.isalnum():
        raise ValidationError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only alphanumeric characters are allowed (e.g. BTCUSDT)."
        )
    if len(symbol) > SYMBOL_MAX_LENGTH:
        raise ValidationError(
            f"Symbol '{symbol}' is too long (max {SYMBOL_MAX_LENGTH} chars)."
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Ensure side is BUY or SELL.

    Returns:
        Normalised (uppercase) side string.

    Raises:
        ValidationError: if side is not in VALID_SIDES.
    """
    if not side or not isinstance(side, str):
        raise ValidationError("Side must be a non-empty string.")

    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Ensure order_type is one of the supported types.

    Returns:
        Normalised (uppercase) order type string.

    Raises:
        ValidationError: if order_type is not supported.
    """
    if not order_type or not isinstance(order_type, str):
        raise ValidationError("Order type must be a non-empty string.")

    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    """
    Ensure quantity is a positive decimal number.

    Returns:
        Validated quantity as a Decimal.

    Raises:
        ValidationError: if quantity is not a positive number.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid quantity '{quantity}'. Must be a positive number."
        )

    if qty <= MIN_POSITIVE:
        raise ValidationError(
            f"Quantity must be greater than {MIN_POSITIVE}. Got: {qty}."
        )
    return qty


def validate_price(
    price: Optional[str | float | Decimal],
    order_type: str,
) -> Optional[Decimal]:
    """
    Validate price field.

    - MARKET orders: price must be None / omitted.
    - LIMIT / STOP_MARKET orders: price must be a positive decimal.

    Returns:
        Validated price as Decimal, or None for MARKET orders.

    Raises:
        ValidationError: on constraint violation.
    """
    order_type = order_type.strip().upper()

    if order_type in ("MARKET", "STOP_MARKET"):
        if price is not None and str(price).strip() not in ("", "0", "0.0"):
            raise ValidationError(
                f"Price should not be specified for {order_type} orders."
            )
        return None

    # LIMIT requires a price
    if price is None or str(price).strip() == "":
        raise ValidationError(
            f"Price is required for {order_type} orders."
        )

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid price '{price}'. Must be a positive number."
        )

    if p <= MIN_POSITIVE:
        raise ValidationError(
            f"Price must be greater than {MIN_POSITIVE}. Got: {p}."
        )
    return p


def validate_stop_price(
    stop_price: Optional[str | float | Decimal],
    order_type: str,
) -> Optional[Decimal]:
    """
    Validate stop price for STOP_MARKET orders.

    Returns:
        Validated stop price as Decimal, or None.

    Raises:
        ValidationError: on constraint violation.
    """
    if order_type.upper() != "STOP_MARKET":
        return None

    if stop_price is None or str(stop_price).strip() == "":
        raise ValidationError("stopPrice is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid stop price '{stop_price}'. Must be a positive number."
        )

    if sp <= MIN_POSITIVE:
        raise ValidationError(
            f"Stop price must be greater than {MIN_POSITIVE}. Got: {sp}."
        )
    return sp


def validate_all(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float | Decimal,
    price: Optional[str | float | Decimal] = None,
    stop_price: Optional[str | float | Decimal] = None,
) -> dict:
    """
    Run all validators and return a clean, normalised parameter dict.

    Returns:
        Dict with keys: symbol, side, order_type, quantity, price, stop_price.

    Raises:
        ValidationError: on the first constraint violation encountered.
    """
    validated_symbol = validate_symbol(symbol)
    validated_side = validate_side(side)
    validated_order_type = validate_order_type(order_type)
    validated_quantity = validate_quantity(quantity)
    validated_price = validate_price(price, validated_order_type)
    validated_stop_price = validate_stop_price(stop_price, validated_order_type)

    return {
        "symbol": validated_symbol,
        "side": validated_side,
        "order_type": validated_order_type,
        "quantity": validated_quantity,
        "price": validated_price,
        "stop_price": validated_stop_price,
    }
