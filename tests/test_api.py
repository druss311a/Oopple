"""Comprehensive integration tests for Oopple FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from oopple.api.app import app
from oopple.core.database import get_session
from oopple.services.catalog_service import CatalogService
from oopple.services.hydration_service import HydrationService
from oopple.services.optimizer_service import OptimizerService


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    # Seed in-memory DB
    with Session(test_engine) as session:
        cat_svc = CatalogService(session)
        cat_svc.seed_defaults_if_empty()
        opt_svc = OptimizerService(session)
        opt_svc.seed_recipes_if_empty()
        hyd_svc = HydrationService(session)
        hyd_svc.ensure_default_user_and_water_preference()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_catalog_search(client: TestClient):
    response = client.get("/api/catalog?q=water")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["sku"] == "OO-WATER-001"


def test_api_hydration_flow(client: TestClient):
    # Check initial status
    status_resp = client.get("/api/hydration/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert "Trust us, your body likes water" in status["preference_note"]

    # Log 500ml water
    log_resp = client.post(
        "/api/hydration/log", json={"amount_ml": 500.0, "source_name": "Glass of water"}
    )
    assert log_resp.status_code == 201
    log_data = log_resp.json()
    assert log_data["delta_water_ml"] == 500.0

    # Verify updated status
    status_resp2 = client.get("/api/hydration/status")
    status2 = status_resp2.json()
    assert status2["direct_water_ml"] >= 500.0


def test_api_inventory_and_optimizer_flow(client: TestClient):
    # Ingest Chicken into inventory
    ingest_resp = client.post(
        "/api/inventory/ingest",
        json={
            "intake_unit_id": 2,
            "quantity": 500.0,
            "unit": "g",
            "storage_location": "fridge",
            "cost_basis": 7.50,
            "source": "butcher",
        },
    )
    assert ingest_resp.status_code == 201

    # Ingest Spinach into inventory
    ingest_resp2 = client.post(
        "/api/inventory/ingest",
        json={
            "intake_unit_id": 6,
            "quantity": 200.0,
            "unit": "g",
            "storage_location": "fridge",
            "cost_basis": 2.99,
        },
    )
    assert ingest_resp2.status_code == 201

    # Check optimizer suggestions
    opt_resp = client.get("/api/optimizer/suggest")
    assert opt_resp.status_code == 200
    suggestions = opt_resp.json()
    assert len(suggestions) > 0
    assert any("Chicken" in s["recipe_name"] for s in suggestions)

    # Verify ledger integrity
    verify_resp = client.get("/api/ledger/verify")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_valid"] is True
