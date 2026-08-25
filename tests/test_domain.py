"""Tests for domain models, conversions, and entities."""

from oopple.domain.enums import CuisineType, ItemCategory, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.units import convert_quantity


def test_unit_conversions():
    # Mass conversions
    assert convert_quantity(1.0, UnitType.POUND, UnitType.GRAM) == 453.592
    assert round(convert_quantity(100.0, UnitType.GRAM, UnitType.OUNCE), 2) == 3.53

    # Volume conversions
    assert round(convert_quantity(1.0, UnitType.CUP, UnitType.MILLILITER), 1) == 236.6
    assert round(convert_quantity(3.0, UnitType.TEASPOON, UnitType.TABLESPOON), 1) == 1.0


def test_intake_unit_creation():
    apple = IntakeUnit(
        sku="OO-APPLE-001",
        name="Honeycrisp Apple",
        brand="Local Orchard",
        category=ItemCategory.PRODUCE,
        cuisine_type=CuisineType.AMERICANA,
        serving_size=100.0,
        serving_unit=UnitType.GRAM,
        calories=52.0,
        protein_g=0.3,
        carbs_g=14.0,
        fat_g=0.2,
        fiber_g=2.4,
        water_ml=85.0,
        shelf_life_fridge_days=21,
        shelf_life_counter_days=7,
        default_cost=0.75,
    )
    assert apple.sku == "OO-APPLE-001"
    assert apple.water_ml == 85.0
    assert apple.calories == 52.0
