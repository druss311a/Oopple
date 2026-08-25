"""Ledger domain model - immutable event log for nutrition and costs."""

import hashlib
import json
from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel

from oopple.domain.enums import EventType, UnitType
from oopple.domain.intake_unit import IntakeUnit

GENESIS_PREV_HASH = "0" * 64


class LedgerEntryBase(SQLModel):
    sequence_number: int = Field(
        index=True,
        unique=True,
        description="Strictly monotonic sequence ID",
    )
    prev_hash: str = Field(description="SHA-256 hash of the previous ledger block")
    current_hash: str = Field(index=True, description="SHA-256 hash of this ledger entry")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )
    event_type: EventType = Field(index=True)
    intake_unit_id: int = Field(foreign_key="intake_units.id", index=True)
    quantity: float = Field(default=1.0)
    unit: UnitType = Field(default=UnitType.GRAM)

    # Nutritional changes logged to user body state
    delta_calories: float = Field(default=0.0)
    delta_protein_g: float = Field(default=0.0)
    delta_carbs_g: float = Field(default=0.0)
    delta_fat_g: float = Field(default=0.0)
    delta_water_ml: float = Field(default=0.0)

    # Financial value delta
    cost_delta: float = Field(
        default=0.0,
        description="Positive for expenditure, negative for depreciation",
    )
    notes: str | None = Field(default=None)


class LedgerEntry(LedgerEntryBase, table=True):
    __tablename__ = "ledger_entries"

    id: int | None = Field(default=None, primary_key=True)
    intake_unit: IntakeUnit | None = Relationship()


def compute_entry_hash(
    sequence_number: int,
    prev_hash: str,
    timestamp: datetime,
    event_type: str,
    intake_unit_id: int,
    quantity: float,
    unit: str,
    delta_calories: float,
    delta_protein_g: float,
    delta_carbs_g: float,
    delta_fat_g: float,
    delta_water_ml: float,
    cost_delta: float,
    notes: str | None = None,
) -> str:
    """Compute deterministic SHA-256 hash for a ledger block."""
    # Ensure UTC timestamp is normalized consistently
    ts_normalized = (
        timestamp.replace(tzinfo=UTC).isoformat()
        if timestamp.tzinfo is None
        else timestamp.astimezone(UTC).isoformat()
    )

    payload = {
        "sequence_number": sequence_number,
        "prev_hash": prev_hash,
        "timestamp": ts_normalized,
        "event_type": str(event_type),
        "intake_unit_id": intake_unit_id,
        "quantity": round(quantity, 4),
        "unit": str(unit),
        "delta_calories": round(delta_calories, 2),
        "delta_protein_g": round(delta_protein_g, 2),
        "delta_carbs_g": round(delta_carbs_g, 2),
        "delta_fat_g": round(delta_fat_g, 2),
        "delta_water_ml": round(delta_water_ml, 2),
        "cost_delta": round(cost_delta, 2),
        "notes": notes or "",
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
