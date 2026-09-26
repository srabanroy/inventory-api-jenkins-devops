"""Integration tests exercise HTTP routing, authentication, persistence, and metrics."""


def test_dashboard_serves_inventory_frontend(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Inventory workspace" in body
    assert 'id="inventory-table"' in body
    assert 'src="/static/app.js"' in body


def test_frontend_assets_are_packaged(client):
    stylesheet = client.get("/static/styles.css")
    script = client.get("/static/app.js")

    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert "Inventory dashboard" in script.get_data(as_text=True)


def test_health_reports_database_readiness(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"database": True, "status": "ok"}


def test_version_reports_environment(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.get_json() == {"environment": "test", "version": "development"}


def test_inventory_requires_api_key(client):
    response = client.get("/api/items")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorised"


def test_crud_round_trip(client, authorised_headers):
    created = client.post(
        "/api/items",
        json={"sku": "KB-001", "name": "Mechanical keyboard", "quantity": 5},
        headers=authorised_headers,
    )
    assert created.status_code == 201
    item_id = created.get_json()["id"]

    listed = client.get("/api/items", headers=authorised_headers)
    assert [item["sku"] for item in listed.get_json()["items"]] == ["KB-001"]

    updated = client.put(
        f"/api/items/{item_id}",
        json={"sku": "KB-001", "name": "Mechanical keyboard", "quantity": 7},
        headers=authorised_headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["quantity"] == 7

    deleted = client.delete(f"/api/items/{item_id}", headers=authorised_headers)
    assert deleted.status_code == 200

    missing = client.get(f"/api/items/{item_id}", headers=authorised_headers)
    assert missing.status_code == 404


def test_duplicate_sku_returns_conflict(client, authorised_headers):
    payload = {"sku": "DUP-1", "name": "Duplicate test", "quantity": 1}
    assert client.post("/api/items", json=payload, headers=authorised_headers).status_code == 201
    response = client.post("/api/items", json=payload, headers=authorised_headers)
    assert response.status_code == 409
    assert response.get_json()["error"] == "sku_already_exists"


def test_invalid_item_returns_all_validation_errors(client, authorised_headers):
    response = client.post(
        "/api/items",
        json={"sku": "", "name": "", "quantity": -2},
        headers=authorised_headers,
    )
    assert response.status_code == 400
    assert len(response.get_json()["details"]) == 3


def test_update_missing_item_returns_not_found(client, authorised_headers):
    response = client.put(
        "/api/items/999",
        json={"sku": "MISS-1", "name": "Missing", "quantity": 1},
        headers=authorised_headers,
    )
    assert response.status_code == 404


def test_delete_missing_item_returns_not_found(client, authorised_headers):
    response = client.delete("/api/items/999", headers=authorised_headers)
    assert response.status_code == 404


def test_metrics_include_request_and_readiness_series(client):
    client.get("/health")
    response = client.get("/metrics")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "inventory_http_requests_total" in body
    assert "inventory_readiness 1.0" in body
