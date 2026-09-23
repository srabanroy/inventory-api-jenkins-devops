"""Flask routes, authentication, error handling, and application metrics."""

from __future__ import annotations

import hmac
import os
import sqlite3
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar, cast

from flask import Flask, Response, g, jsonify, request
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from . import db
from .validation import validate_item

ViewFunction = TypeVar("ViewFunction", bound=Callable[..., Any])


def create_app(test_config: dict[str, Any] | None = None) -> Flask:  # noqa: C901
    """Create an isolated Flask application suitable for production and tests."""
    app = Flask(__name__)
    environment = os.getenv("APP_ENV", "development")
    api_key = os.getenv("INVENTORY_API_KEY")
    if environment == "production" and not api_key and not test_config:
        raise RuntimeError("INVENTORY_API_KEY must be configured in production")

    app.config.from_mapping(
        DATABASE=os.getenv("DATABASE_PATH", str(Path("data") / "inventory.db")),
        API_KEY=api_key or "local-development-key",
        ENVIRONMENT=environment,
    )
    if test_config:
        app.config.update(test_config)

    db.initialise(app.config["DATABASE"])

    registry = CollectorRegistry(auto_describe=True)
    request_count = Counter(
        "inventory_http_requests_total",
        "Total HTTP requests processed by the inventory API",
        ("method", "route", "status"),
        registry=registry,
    )
    request_latency = Histogram(
        "inventory_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ("method", "route"),
        registry=registry,
    )
    readiness = Gauge(
        "inventory_readiness",
        "Whether the inventory database is ready",
        registry=registry,
    )

    def require_api_key(view: ViewFunction) -> ViewFunction:
        """Protect stateful and inventory-reading endpoints with a constant-time check."""

        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            supplied = request.headers.get("X-API-Key", "")
            expected = str(app.config["API_KEY"])
            if not supplied or not hmac.compare_digest(supplied, expected):
                return jsonify(error="unauthorised"), 401
            return view(*args, **kwargs)

        return cast(ViewFunction, wrapped)

    @app.before_request
    def start_request_timer() -> None:
        g.request_started_at = time.perf_counter()

    @app.after_request
    def record_request_metrics(response: Response) -> Response:
        route = request.url_rule.rule if request.url_rule else "unmatched"
        elapsed = time.perf_counter() - g.get("request_started_at", time.perf_counter())
        request_count.labels(request.method, route, str(response.status_code)).inc()
        request_latency.labels(request.method, route).observe(elapsed)
        return response

    @app.get("/health")
    def health() -> tuple[Response, int]:
        ready = db.database_is_ready(app.config["DATABASE"])
        readiness.set(1 if ready else 0)
        status = 200 if ready else 503
        return jsonify(status="ok" if ready else "unavailable", database=ready), status

    @app.get("/metrics")
    def metrics() -> Response:
        readiness.set(1 if db.database_is_ready(app.config["DATABASE"]) else 0)
        return Response(generate_latest(registry), mimetype="text/plain; version=0.0.4")

    @app.get("/api/items")
    @require_api_key
    def items_index() -> Response:
        return jsonify(items=db.list_items(app.config["DATABASE"]))

    @app.post("/api/items")
    @require_api_key
    def items_create() -> tuple[Response, int]:
        item, errors = validate_item(request.get_json(silent=True))
        if errors or item is None:
            return jsonify(error="validation_failed", details=errors), 400
        try:
            created = db.create_item(app.config["DATABASE"], **item)
        except sqlite3.IntegrityError:
            return jsonify(error="sku_already_exists"), 409
        return jsonify(created), 201

    @app.get("/api/items/<int:item_id>")
    @require_api_key
    def items_show(item_id: int) -> tuple[Response, int] | Response:
        item = db.get_item(app.config["DATABASE"], item_id)
        if item is None:
            return jsonify(error="not_found"), 404
        return jsonify(item)

    @app.put("/api/items/<int:item_id>")
    @require_api_key
    def items_update(item_id: int) -> tuple[Response, int] | Response:
        item, errors = validate_item(request.get_json(silent=True))
        if errors or item is None:
            return jsonify(error="validation_failed", details=errors), 400
        try:
            updated = db.update_item(app.config["DATABASE"], item_id, **item)
        except sqlite3.IntegrityError:
            return jsonify(error="sku_already_exists"), 409
        if updated is None:
            return jsonify(error="not_found"), 404
        return jsonify(updated)

    @app.delete("/api/items/<int:item_id>")
    @require_api_key
    def items_delete(item_id: int) -> tuple[Response, int]:
        if not db.delete_item(app.config["DATABASE"], item_id):
            return jsonify(error="not_found"), 404
        return jsonify(status="deleted"), 200

    return app
