"""Request validation kept separate from HTTP transport for focused unit tests."""

from __future__ import annotations

from typing import Any


def validate_item(payload: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate and normalise an item payload without silently coercing invalid types."""
    if not isinstance(payload, dict):
        return None, ["Request body must be a JSON object"]

    errors: list[str] = []
    sku = payload.get("sku")
    name = payload.get("name")
    quantity = payload.get("quantity")

    if not isinstance(sku, str) or not sku.strip():
        errors.append("sku must be a non-empty string")
    elif len(sku.strip()) > 40:
        errors.append("sku must contain at most 40 characters")

    if not isinstance(name, str) or not name.strip():
        errors.append("name must be a non-empty string")
    elif len(name.strip()) > 120:
        errors.append("name must contain at most 120 characters")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        errors.append("quantity must be a non-negative integer")

    if errors:
        return None, errors

    return {"sku": sku.strip(), "name": name.strip(), "quantity": quantity}, []
