"""Tests for the CatalogService and OpenFoodFacts integration."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oopple.domain.enums import ItemCategory
from oopple.services.catalog_service import CatalogService


@pytest.fixture
def catalog_session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        yield sess


def test_catalog_seeding_and_search(catalog_session: Session):
    service = CatalogService(catalog_session)
    inserted = service.seed_defaults_if_empty()
    assert inserted > 0

    # Test baseline water item exists
    water = service.get_by_sku("OO-WATER-001")
    assert water is not None
    assert water.water_ml == 250.0

    # Test searching by text
    results = service.search(query="spinach")
    assert len(results) >= 1
    assert results[0].name == "Baby Spinach Leaves"

    # Test searching by category
    produce_items = service.search(category=ItemCategory.PRODUCE)
    assert len(produce_items) >= 2


def test_barcode_lookup_local(catalog_session: Session):
    service = CatalogService(catalog_session)
    service.seed_defaults_if_empty()

    # Barcode for chicken from seed catalog
    chicken = service.get_by_barcode("000000000002")
    assert chicken is not None
    assert chicken.sku == "OO-CHICKEN-001"
