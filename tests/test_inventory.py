"""Tests for InventoryService lifecycle, storage transitions, and decay."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oopple.domain.enums import ExpiryUrgency, StorageLocation, UnitType
from oopple.domain.inventory import InventoryItem
from oopple.services.catalog_service import CatalogService
from oopple.services.inventory_service import InventoryService


@pytest.fixture
def inv_session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        cat_svc = CatalogService(sess)
        cat_svc.seed_defaults_if_empty()
        yield sess


def test_inventory_decay_urgency(inv_session: Session):
    service = InventoryService(inv_session)
    now = datetime.now(UTC)

    # Add item expiring in 12 hours -> CRITICAL_TODAY
    item1 = InventoryItem(
        intake_unit_id=2,  # Chicken
        storage_location=StorageLocation.FRIDGE,
        quantity=500.0,
        unit=UnitType.GRAM,
        expiry_date=now + timedelta(hours=12),
    )
    # Add item expiring in 2.5 days -> USE_SOON
    item2 = InventoryItem(
        intake_unit_id=6,  # Spinach
        storage_location=StorageLocation.FRIDGE,
        quantity=150.0,
        unit=UnitType.GRAM,
        expiry_date=now + timedelta(days=2, hours=12),
    )
    # Add item expiring in 14 days -> FRESH
    item3 = InventoryItem(
        intake_unit_id=4,  # Eggs
        storage_location=StorageLocation.FRIDGE,
        quantity=12.0,
        unit=UnitType.PIECE,
        expiry_date=now + timedelta(days=14),
    )

    inv_session.add_all([item1, item2, item3])
    inv_session.commit()

    statuses = service.list_inventory()
    assert len(statuses) == 3
    urgencies = [s.urgency for s in statuses]
    assert ExpiryUrgency.CRITICAL_TODAY in urgencies
    assert ExpiryUrgency.USE_SOON in urgencies
    assert ExpiryUrgency.FRESH in urgencies


def test_move_location_extends_expiry(inv_session: Session):
    service = InventoryService(inv_session)
    now = datetime.now(UTC)

    item = InventoryItem(
        intake_unit_id=2,  # Chicken (shelf_life_freezer_days = 180)
        storage_location=StorageLocation.FRIDGE,
        quantity=500.0,
        unit=UnitType.GRAM,
        expiry_date=now + timedelta(days=2),
    )
    inv_session.add(item)
    inv_session.commit()
    inv_session.refresh(item)

    # Move from fridge to freezer
    updated = service.move_item_location(item.id, StorageLocation.FREEZER)
    assert updated.storage_location == StorageLocation.FREEZER
    days_to_new_expiry = (updated.expiry_date.replace(tzinfo=UTC) - now).days
    assert days_to_new_expiry >= 170
