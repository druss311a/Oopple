"""Unit conversion utilities for nutritional scaling and recipe management."""

from oopple.domain.enums import UnitType

# Standard conversion multipliers to base units (GRAM for mass, MILLILITER for volume)
MASS_TO_GRAM: dict[UnitType, float] = {
    UnitType.GRAM: 1.0,
    UnitType.OUNCE: 28.3495,
    UnitType.POUND: 453.592,
}

VOLUME_TO_ML: dict[UnitType, float] = {
    UnitType.MILLILITER: 1.0,
    UnitType.CUP: 236.588,
    UnitType.TABLESPOON: 14.7868,
    UnitType.TEASPOON: 4.92892,
}


def convert_quantity(
    amount: float,
    from_unit: UnitType,
    to_unit: UnitType,
    serving_mass_g: float | None = None,
    serving_volume_ml: float | None = None,
) -> float:
    """Convert quantity from one unit to another.

    Supports direct mass-to-mass and volume-to-volume, as well as serving/piece conversions
    when item metrics are provided.
    """
    if from_unit == to_unit:
        return amount

    # Mass conversions
    if from_unit in MASS_TO_GRAM and to_unit in MASS_TO_GRAM:
        grams = amount * MASS_TO_GRAM[from_unit]
        return grams / MASS_TO_GRAM[to_unit]

    # Volume conversions
    if from_unit in VOLUME_TO_ML and to_unit in VOLUME_TO_ML:
        ml = amount * VOLUME_TO_ML[from_unit]
        return ml / VOLUME_TO_ML[to_unit]

    # Piece / Serving conversions
    if from_unit in (UnitType.PIECE, UnitType.SERVING) and to_unit in MASS_TO_GRAM:
        base_g = serving_mass_g or 100.0
        total_g = amount * base_g
        return total_g / MASS_TO_GRAM[to_unit]

    if from_unit in MASS_TO_GRAM and to_unit in (UnitType.PIECE, UnitType.SERVING):
        grams = amount * MASS_TO_GRAM[from_unit]
        base_g = serving_mass_g or 100.0
        return grams / base_g

    if from_unit in (UnitType.PIECE, UnitType.SERVING) and to_unit in VOLUME_TO_ML:
        base_ml = serving_volume_ml or 250.0
        total_ml = amount * base_ml
        return total_ml / VOLUME_TO_ML[to_unit]

    # Default fallback: 1:1 if unknown cross-conversion
    return amount
