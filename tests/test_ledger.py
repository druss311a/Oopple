"""Tests for the Nutrition & Cost Ledger cryptographic integrity and aggregations."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oopple.domain.enums import CuisineType, EventType, ItemCategory, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.services.ledger_service import LedgerService


@pytest.fixture
def session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        # Seed test items
        water = IntakeUnit(
            sku="OO-WATER-001",
            name="Spring Water",
            category=ItemCategory.BEVERAGE,
            cuisine_type=CuisineType.BEVERAGE,
            serving_size=250.0,
            serving_unit=UnitType.MILLILITER,
            calories=0.0,
            protein_g=0.0,
            carbs_g=0.0,
            fat_g=0.0,
            water_ml=250.0,
            default_cost=0.0,
        )
        chicken = IntakeUnit(
            sku="OO-CHICKEN-001",
            name="Chicken Breast",
            category=ItemCategory.PROTEIN,
            cuisine_type=CuisineType.GLOBAL,
            serving_size=100.0,
            serving_unit=UnitType.GRAM,
            calories=165.0,
            protein_g=31.0,
            carbs_g=0.0,
            fat_g=3.6,
            water_ml=65.0,
            default_cost=4.50,
        )
        sess.add(water)
        sess.add(chicken)
        sess.commit()
        yield sess


def test_ledger_append_and_verify(session: Session):
    service = LedgerService(session)

    # 1. Acquire chicken
    entry1 = service.record_event(
        event_type=EventType.ACQUIRE,
        intake_unit_id=2,
        quantity=500.0,
        unit=UnitType.GRAM,
        cost_delta=9.00,
        notes="Purchased organic chicken breast",
    )
    assert entry1.sequence_number == 1
    assert entry1.prev_hash == "0" * 64
    assert entry1.delta_protein_g == 0.0  # Not consumed yet

    # 2. Consume 200g of chicken
    entry2 = service.record_event(
        event_type=EventType.CONSUME,
        intake_unit_id=2,
        quantity=200.0,
        unit=UnitType.GRAM,
        notes="Lunch grill",
    )
    assert entry2.sequence_number == 2
    assert entry2.prev_hash == entry1.current_hash
    assert entry2.delta_calories == 330.0
    assert entry2.delta_protein_g == 62.0

    # 3. Log 500ml water hydration
    entry3 = service.record_event(
        event_type=EventType.HYDRATE,
        intake_unit_id=1,
        quantity=500.0,
        unit=UnitType.MILLILITER,
        notes="Morning hydration",
    )
    assert entry3.sequence_number == 3
    assert entry3.prev_hash == entry2.current_hash
    assert entry3.delta_water_ml == 500.0

    # Verify blockchain-style integrity
    valid, msg = service.verify_ledger_integrity()
    assert valid is True
    assert "3 blocks valid" in msg

    # Check daily summary
    summary = service.get_daily_summary()
    assert summary["total_calories"] == 330.0
    assert summary["total_protein_g"] == 62.0
    assert summary["total_water_ml"] == 630.0  # 500ml water + (65ml * 2) from chicken!
    assert summary["spend_today"] == 9.00


def test_ledger_tamper_detection(session: Session):
    service = LedgerService(session)
    service.record_event(
        EventType.ACQUIRE,
        intake_unit_id=1,
        quantity=100.0,
        unit=UnitType.MILLILITER,
    )
    entry2 = service.record_event(
        EventType.CONSUME,
        intake_unit_id=2,
        quantity=100.0,
        unit=UnitType.GRAM,
    )

    # Tamper with an entry behind the service's back
    entry2.delta_protein_g = 999.0
    session.add(entry2)
    session.commit()

    valid, msg = service.verify_ledger_integrity()
    assert valid is False
    assert "Tampered block" in msg
