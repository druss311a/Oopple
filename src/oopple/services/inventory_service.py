"""Inventory Service - managing stock lifecycle, dynamic location decay, and consumption/waste."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from oopple.domain.enums import EventType, ExpiryUrgency, StorageLocation, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.inventory import InventoryItem
from oopple.domain.units import convert_quantity
from oopple.services.ledger_service import LedgerService


class InventoryItemStatus:
    def __init__(
        self,
        item: InventoryItem,
        intake_unit: IntakeUnit,
        days_remaining: float,
        urgency: ExpiryUrgency,
    ):
        self.item = item
        self.intake_unit = intake_unit
        self.days_remaining = round(days_remaining, 1)
        self.urgency = urgency


class InventoryService:
    def __init__(self, session: Session):
        self.session = session
        self.ledger_service = LedgerService(session)

    def get_item(self, item_id: int) -> InventoryItem | None:
        """Get inventory item by ID."""
        return self.session.get(InventoryItem, item_id)

    def list_inventory(
        self,
        location: StorageLocation | None = None,
        include_depleted: bool = False,
    ) -> list[InventoryItemStatus]:
        """List active inventory items with calculated shelf-life decay status."""
        statement = select(InventoryItem).order_by(col(InventoryItem.expiry_date).asc())

        if not include_depleted:
            statement = statement.where(InventoryItem.quantity > 0.0)

        if location:
            statement = statement.where(InventoryItem.storage_location == location)

        items = list(self.session.exec(statement).all())
        results: list[InventoryItemStatus] = []

        now = datetime.now(UTC)

        for it in items:
            intake_unit = self.session.get(IntakeUnit, it.intake_unit_id)
            if not intake_unit:
                continue

            # Ensure expiry_date is timezone-aware
            expiry = (
                it.expiry_date.replace(tzinfo=UTC)
                if it.expiry_date.tzinfo is None
                else it.expiry_date.astimezone(UTC)
            )
            seconds_left = (expiry - now).total_seconds()
            days_left = seconds_left / 86400.0

            if days_left < 0:
                urgency = ExpiryUrgency.EXPIRED
            elif days_left <= 1.0:
                urgency = ExpiryUrgency.CRITICAL_TODAY
            elif days_left <= 3.0:
                urgency = ExpiryUrgency.USE_SOON
            else:
                urgency = ExpiryUrgency.FRESH

            results.append(
                InventoryItemStatus(
                    item=it,
                    intake_unit=intake_unit,
                    days_remaining=days_left,
                    urgency=urgency,
                )
            )

        return results

    def move_item_location(
        self,
        item_id: int,
        target_location: StorageLocation,
    ) -> InventoryItem:
        """Transfer item between locations (e.g. Fridge -> Freezer) with decay adjustments."""
        item = self.get_item(item_id)
        if not item:
            raise ValueError(f"Inventory item #{item_id} not found.")

        intake_unit = self.session.get(IntakeUnit, item.intake_unit_id)
        if not intake_unit:
            raise ValueError(f"IntakeUnit #{item.intake_unit_id} not found.")

        old_loc = item.storage_location
        if old_loc == target_location:
            return item

        now = datetime.now(UTC)

        # Dynamic shelf-life extension/reduction
        if target_location == StorageLocation.FREEZER:
            # Freezing preserves fresh food for freezer shelf-life days
            freezer_days = intake_unit.shelf_life_freezer_days or 120
            item.expiry_date = now + timedelta(days=freezer_days)
        elif target_location == StorageLocation.FRIDGE:
            fridge_days = intake_unit.shelf_life_fridge_days or 7
            item.expiry_date = now + timedelta(days=fridge_days)
        else:
            pantry_days = intake_unit.shelf_life_pantry_days or 14
            item.expiry_date = now + timedelta(days=pantry_days)

        item.storage_location = target_location
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)

        # Record movement in ledger
        self.ledger_service.record_event(
            event_type=EventType.STORE,
            intake_unit_id=item.intake_unit_id,
            quantity=item.quantity,
            unit=item.unit,
            notes=f"Moved from {old_loc.value} to {target_location.value}",
        )

        return item

    def consume_item(
        self,
        item_id: int,
        quantity_to_consume: float,
        unit: UnitType | None = None,
        notes: str | None = None,
    ) -> tuple[InventoryItem | None, float]:
        """Consume a quantity of an inventory item and log it to the nutritional ledger."""
        item = self.get_item(item_id)
        if not item:
            raise ValueError(f"Inventory item #{item_id} not found.")

        target_unit = unit or item.unit
        # Normalize quantity to item unit
        consumed_in_item_unit = convert_quantity(
            quantity_to_consume,
            target_unit,
            item.unit,
        )

        if consumed_in_item_unit > item.quantity:
            consumed_in_item_unit = item.quantity

        remaining = item.quantity - consumed_in_item_unit
        item.quantity = remaining

        if remaining <= 0.001:
            self.session.delete(item)
            item_result = None
        else:
            self.session.add(item)
            item_result = item

        self.session.commit()

        # Log consumption to ledger
        self.ledger_service.record_event(
            event_type=EventType.CONSUME,
            intake_unit_id=item.intake_unit_id,
            quantity=quantity_to_consume,
            unit=target_unit,
            notes=notes or "Consumed from inventory",
        )

        return item_result, consumed_in_item_unit

    def discard_waste_item(
        self,
        item_id: int,
        reason: str = "Expired / Spoiled",
    ) -> float:
        """Discard an expired item and record financial and nutritional waste in ledger."""
        item = self.get_item(item_id)
        if not item:
            raise ValueError(f"Inventory item #{item_id} not found.")

        wasted_cost = item.cost_basis
        intake_id = item.intake_unit_id
        qty = item.quantity
        unit = item.unit

        self.session.delete(item)
        self.session.commit()

        # Record waste in ledger
        self.ledger_service.record_event(
            event_type=EventType.WASTE_DISCARD,
            intake_unit_id=intake_id,
            quantity=qty,
            unit=unit,
            cost_delta=wasted_cost,
            notes=f"Waste depreciation: {reason}",
        )

        return wasted_cost
