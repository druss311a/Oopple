"""Tests for the Multi-Objective Optimizer and recipe matching."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oopple.domain.enums import StorageLocation, UnitType
from oopple.domain.inventory import InventoryItem
from oopple.services.catalog_service import CatalogService
from oopple.services.optimizer_service import OptimizerService


@pytest.fixture
def opt_session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        cat_svc = CatalogService(sess)
        cat_svc.seed_defaults_if_empty()
        opt_svc = OptimizerService(sess)
        opt_svc.seed_recipes_if_empty()
        yield sess


def test_optimizer_prioritizes_expiring_ingredients(opt_session: Session):
    opt_svc = OptimizerService(opt_session)
    now = datetime.now(UTC)

    # Put chicken in fridge expiring today! (ID: 2)
    chicken_batch = InventoryItem(
        intake_unit_id=2,
        storage_location=StorageLocation.FRIDGE,
        quantity=400.0,
        unit=UnitType.GRAM,
        expiry_date=now + timedelta(hours=10),
    )
    # Put spinach in fridge (ID: 6)
    spinach_batch = InventoryItem(
        intake_unit_id=6,
        storage_location=StorageLocation.FRIDGE,
        quantity=200.0,
        unit=UnitType.GRAM,
        expiry_date=now + timedelta(days=2),
    )
    # Put olive oil in pantry (ID: 8)
    oil_batch = InventoryItem(
        intake_unit_id=8,
        storage_location=StorageLocation.PANTRY,
        quantity=500.0,
        unit=UnitType.MILLILITER,
        expiry_date=now + timedelta(days=180),
    )
    opt_session.add_all([chicken_batch, spinach_batch, oil_batch])
    opt_session.commit()

    recommendations = opt_svc.suggest_meals()
    assert len(recommendations) > 0

    # Top recommendation should be Mediterranean Chicken & Spinach Bowl!
    top = recommendations[0]
    assert "Chicken" in top.recipe.name
    assert top.inventory_match_ratio == 1.0
    assert len(top.expiring_ingredients_used) >= 1
