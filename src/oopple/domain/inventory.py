"""Inventory domain models - tracking stored physical items and batches across locations."""

from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel

from oopple.domain.enums import StorageLocation, UnitType
from oopple.domain.intake_unit import IntakeUnit


class InventoryItemBase(SQLModel):
    intake_unit_id: int = Field(foreign_key="intake_units.id", index=True)
    storage_location: StorageLocation = Field(default=StorageLocation.FRIDGE, index=True)
    quantity: float = Field(default=1.0, ge=0.0)
    unit: UnitType = Field(default=UnitType.PIECE)
    cost_basis: float = Field(default=0.0, ge=0.0, description="Cost paid for this batch")
    acquisition_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expiry_date: datetime = Field(index=True)
    source: str = Field(default="grocery", description="grocery, garden_harvest, market, prep")
    batch_code: str | None = Field(default=None)
    is_opened: bool = Field(default=False)
    notes: str | None = Field(default=None)


class InventoryItem(InventoryItemBase, table=True):
    __tablename__ = "inventory_items"

    id: int | None = Field(default=None, primary_key=True)
    intake_unit: IntakeUnit | None = Relationship()


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemRead(InventoryItemBase):
    id: int
    intake_unit: IntakeUnit | None = None
