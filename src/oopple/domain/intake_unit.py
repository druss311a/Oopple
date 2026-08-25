"""Intake Unit domain model - the atomic entity of food, ingredients, and hydration."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from oopple.domain.enums import CuisineType, ItemCategory, UnitType


class IntakeUnitBase(SQLModel):
    sku: str = Field(index=True, unique=True, description="Unique SKU or Hash identifier")
    name: str = Field(index=True)
    brand: str | None = Field(default=None, index=True)
    barcode: str | None = Field(default=None, index=True, description="UPC or EAN barcode")
    cuisine_type: CuisineType = Field(default=CuisineType.GLOBAL, index=True)
    category: ItemCategory = Field(default=ItemCategory.PRODUCE, index=True)

    # Nutritional profile per serving
    serving_size: float = Field(default=100.0)
    serving_unit: UnitType = Field(default=UnitType.GRAM)
    calories: float = Field(default=0.0)
    protein_g: float = Field(default=0.0)
    carbs_g: float = Field(default=0.0)
    fat_g: float = Field(default=0.0)
    fiber_g: float = Field(default=0.0)
    sodium_mg: float = Field(default=0.0)
    water_ml: float = Field(default=0.0, description="Inherent water content in ml")

    # Default shelf life estimations by storage location (days)
    shelf_life_fridge_days: int | None = Field(default=7)
    shelf_life_freezer_days: int | None = Field(default=180)
    shelf_life_pantry_days: int | None = Field(default=14)
    shelf_life_counter_days: int | None = Field(default=5)

    # Financial basis
    default_cost: float = Field(default=0.0, description="Estimated/average purchase cost")
    tags: str = Field(default="", description="Comma-separated tags")


class IntakeUnit(IntakeUnitBase, table=True):
    __tablename__ = "intake_units"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntakeUnitCreate(IntakeUnitBase):
    pass


class IntakeUnitRead(IntakeUnitBase):
    id: int
    created_at: datetime
