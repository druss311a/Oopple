"""Tests for IngestionService parsing and inventory ingestion."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oopple.domain.enums import StorageLocation, UnitType
from oopple.services.catalog_service import CatalogService
from oopple.services.ingestion_service import IngestionService
from oopple.services.ledger_service import LedgerService


@pytest.fixture
def ingestion_session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        cat_service = CatalogService(sess)
        cat_service.seed_defaults_if_empty()
        yield sess


def test_parse_natural_language_grocery_text(ingestion_session: Session):
    service = IngestionService(ingestion_session)

    text = """
    2 lbs Chicken Breast
    500 ml Spring Water
    3 Apples
    """

    parsed = service.parse_natural_language_text(text)
    assert len(parsed) == 3

    assert parsed[0].quantity == 2.0
    assert parsed[0].unit == UnitType.POUND
    assert parsed[0].matched_unit is not None
    assert parsed[0].matched_unit.sku == "OO-CHICKEN-001"

    assert parsed[1].quantity == 500.0
    assert parsed[1].unit == UnitType.MILLILITER
    assert parsed[1].matched_unit is not None
    assert parsed[1].matched_unit.sku == "OO-WATER-001"


def test_ingest_item_into_inventory_and_ledger(ingestion_session: Session):
    service = IngestionService(ingestion_session)
    ledger_svc = LedgerService(ingestion_session)

    # Ingest 2 lbs of chicken to fridge
    inv_item = service.ingest_item(
        intake_unit_id=2,
        quantity=2.0,
        unit=UnitType.POUND,
        storage_location=StorageLocation.FRIDGE,
        cost_basis=9.98,
        source="supermarket",
        notes="Weekly grocery run",
    )

    assert inv_item.id is not None
    assert inv_item.storage_location == StorageLocation.FRIDGE
    assert inv_item.quantity == 2.0

    # Verify ledger was automatically updated
    valid, msg = ledger_svc.verify_ledger_integrity()
    assert valid is True
    assert "1 blocks valid" in msg
