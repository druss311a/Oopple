"""Ledger Service - managing the append-only cryptographic event log for nutrition and costs."""

from datetime import UTC, date, datetime

from sqlmodel import Session, col, select

from oopple.domain.enums import EventType, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.ledger import (
    GENESIS_PREV_HASH,
    LedgerEntry,
    compute_entry_hash,
)
from oopple.domain.units import convert_quantity


class LedgerService:
    def __init__(self, session: Session):
        self.session = session

    def get_latest_entry(self) -> LedgerEntry | None:
        """Get the most recent ledger entry."""
        statement = select(LedgerEntry).order_by(col(LedgerEntry.sequence_number).desc()).limit(1)
        return self.session.exec(statement).first()

    def record_event(
        self,
        event_type: EventType,
        intake_unit_id: int,
        quantity: float,
        unit: UnitType,
        cost_delta: float = 0.0,
        notes: str | None = None,
        custom_timestamp: datetime | None = None,
    ) -> LedgerEntry:
        """Record an intake/depreciation/acquisition event with SHA-256 hash chaining."""
        intake_unit = self.session.get(IntakeUnit, intake_unit_id)
        if not intake_unit:
            raise ValueError(f"IntakeUnit ID {intake_unit_id} does not exist.")

        # Calculate proportional nutritional deltas only for consumption or hydration
        delta_cals = 0.0
        delta_prot = 0.0
        delta_carbs = 0.0
        delta_fat = 0.0
        delta_water = 0.0

        if event_type in (EventType.CONSUME, EventType.HYDRATE):
            # Scale nutrients according to serving size
            ratio = 1.0
            if intake_unit.serving_size > 0:
                is_g = intake_unit.serving_unit == UnitType.GRAM
                is_ml = intake_unit.serving_unit == UnitType.MILLILITER
                serving_g = intake_unit.serving_size if is_g else None
                serving_ml = intake_unit.serving_size if is_ml else None

                normalized_qty = convert_quantity(
                    quantity,
                    unit,
                    intake_unit.serving_unit,
                    serving_mass_g=serving_g,
                    serving_volume_ml=serving_ml,
                )
                ratio = normalized_qty / intake_unit.serving_size

            delta_cals = intake_unit.calories * ratio
            delta_prot = intake_unit.protein_g * ratio
            delta_carbs = intake_unit.carbs_g * ratio
            delta_fat = intake_unit.fat_g * ratio
            delta_water = intake_unit.water_ml * ratio

        # Determine sequence number and previous hash
        latest = self.get_latest_entry()
        if latest is None:
            seq_num = 1
            prev_hash = GENESIS_PREV_HASH
        else:
            seq_num = latest.sequence_number + 1
            prev_hash = latest.current_hash

        entry_time = custom_timestamp or datetime.now(UTC)
        curr_hash = compute_entry_hash(
            sequence_number=seq_num,
            prev_hash=prev_hash,
            timestamp=entry_time,
            event_type=event_type,
            intake_unit_id=intake_unit_id,
            quantity=quantity,
            unit=unit,
            delta_calories=delta_cals,
            delta_protein_g=delta_prot,
            delta_carbs_g=delta_carbs,
            delta_fat_g=delta_fat,
            delta_water_ml=delta_water,
            cost_delta=cost_delta,
            notes=notes,
        )

        entry = LedgerEntry(
            sequence_number=seq_num,
            prev_hash=prev_hash,
            current_hash=curr_hash,
            timestamp=entry_time,
            event_type=event_type,
            intake_unit_id=intake_unit_id,
            quantity=quantity,
            unit=unit,
            delta_calories=delta_cals,
            delta_protein_g=delta_prot,
            delta_carbs_g=delta_carbs,
            delta_fat_g=delta_fat,
            delta_water_ml=delta_water,
            cost_delta=cost_delta,
            notes=notes,
        )

        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def verify_ledger_integrity(self) -> tuple[bool, str]:
        """Verify that the cryptographic hash chain has not been tampered with."""
        statement = select(LedgerEntry).order_by(col(LedgerEntry.sequence_number).asc())
        entries = list(self.session.exec(statement).all())

        if not entries:
            return True, "Ledger is empty (valid)."

        expected_prev_hash = GENESIS_PREV_HASH
        for i, entry in enumerate(entries, start=1):
            if entry.sequence_number != i:
                return False, f"Sequence broken at index {i}: found seq #{entry.sequence_number}"

            if entry.prev_hash != expected_prev_hash:
                prev_short = expected_prev_hash[:8]
                curr_prev_short = entry.prev_hash[:8]
                return False, (
                    f"Hash mismatch at seq #{entry.sequence_number}: "
                    f"expected prev {prev_short}..., found {curr_prev_short}..."
                )

            calculated_hash = compute_entry_hash(
                sequence_number=entry.sequence_number,
                prev_hash=entry.prev_hash,
                timestamp=entry.timestamp,
                event_type=entry.event_type,
                intake_unit_id=entry.intake_unit_id,
                quantity=entry.quantity,
                unit=entry.unit,
                delta_calories=entry.delta_calories,
                delta_protein_g=entry.delta_protein_g,
                delta_carbs_g=entry.delta_carbs_g,
                delta_fat_g=entry.delta_fat_g,
                delta_water_ml=entry.delta_water_ml,
                cost_delta=entry.cost_delta,
                notes=entry.notes,
            )

            if calculated_hash != entry.current_hash:
                return False, f"Tampered block detected at seq #{entry.sequence_number}"

            expected_prev_hash = entry.current_hash

        return True, f"Ledger integrity verified: {len(entries)} blocks valid."

    def get_daily_summary(self, target_date: date | None = None) -> dict:
        """Get aggregate nutritional and cost metrics for a given day."""
        day = target_date or datetime.now(UTC).date()
        start_dt = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=UTC)
        end_dt = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=UTC)

        statement = select(LedgerEntry).where(
            LedgerEntry.timestamp >= start_dt,
            LedgerEntry.timestamp <= end_dt,
        )
        entries = list(self.session.exec(statement).all())

        consumed_types = (EventType.CONSUME, EventType.HYDRATE)
        consumed_entries = [e for e in entries if e.event_type in consumed_types]
        waste_entries = [e for e in entries if e.event_type == EventType.WASTE_DISCARD]
        acquire_entries = [e for e in entries if e.event_type == EventType.ACQUIRE]

        return {
            "date": day.isoformat(),
            "total_calories": round(sum(e.delta_calories for e in consumed_entries), 1),
            "total_protein_g": round(sum(e.delta_protein_g for e in consumed_entries), 1),
            "total_carbs_g": round(sum(e.delta_carbs_g for e in consumed_entries), 1),
            "total_fat_g": round(sum(e.delta_fat_g for e in consumed_entries), 1),
            "total_water_ml": round(sum(e.delta_water_ml for e in consumed_entries), 1),
            "spend_today": round(sum(e.cost_delta for e in acquire_entries), 2),
            "waste_cost_today": round(sum(e.cost_delta for e in waste_entries), 2),
            "event_count": len(entries),
        }
