"""Unit tests for transport-independent item validation."""

from inventory_api.validation import validate_item


def test_valid_item_is_trimmed():
    item, errors = validate_item({"sku": "  A-10  ", "name": "  Keyboard  ", "quantity": 4})
    assert errors == []
    assert item == {"sku": "A-10", "name": "Keyboard", "quantity": 4}


def test_boolean_quantity_is_rejected():
    item, errors = validate_item({"sku": "A-10", "name": "Keyboard", "quantity": True})
    assert item is None
    assert "quantity must be a non-negative integer" in errors


def test_non_object_body_is_rejected():
    item, errors = validate_item(["not", "an", "object"])
    assert item is None
    assert errors == ["Request body must be a JSON object"]


def test_all_invalid_fields_are_reported_together():
    item, errors = validate_item({"sku": "", "name": 12, "quantity": -1})
    assert item is None
    assert len(errors) == 3


def test_long_text_fields_are_rejected():
    item, errors = validate_item({"sku": "S" * 41, "name": "N" * 121, "quantity": 0})
    assert item is None
    assert len(errors) == 2
