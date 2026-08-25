"""Ingestion Service - parsing text, receipt strings, garden logs, and loading into inventory."""

import re
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from oopple.domain.enums import EventType, StorageLocation, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.inventory import InventoryItem
from oopple.services.catalog_service import CatalogService
from oopple.services.ledger_service import LedgerService

UNIT_SYNONYMS: dict[str, UnitType] = {
    "g": UnitType.GRAM,
    "gram": UnitType.GRAM,
    "grams": UnitType.GRAM,
    "ml": UnitType.MILLILITER,
    "milliliter": UnitType.MILLILITER,
    "milliliters": UnitType.MILLILITER,
    "oz": UnitType.OUNCE,
    "ounce": UnitType.OUNCE,
    "ounces": UnitType.OUNCE,
    "lb": UnitType.POUND,
    "lbs": UnitType.POUND,
    "pound": UnitType.POUND,
    "pounds": UnitType.POUND,
    "cup": UnitType.CUP,
    "cups": UnitType.CUP,
    "tbsp": UnitType.TABLESPOON,
    "tablespoon": UnitType.TABLESPOON,
    "tablespoons": UnitType.TABLESPOON,
    "tsp": UnitType.TEASPOON,
    "teaspoon": UnitType.TEASPOON,
    "teaspoons": UnitType.TEASPOON,
    "piece": UnitType.PIECE,
    "pieces": UnitType.PIECE,
    "serving": UnitType.SERVING,
    "servings": UnitType.SERVING,
}


class ParsedIngestionItem:
    def __init__(
        self,
        raw_text: str,
        name: str,
        quantity: float,
        unit: UnitType,
        matched_unit: IntakeUnit | None = None,
        estimated_cost: float = 0.0,
    ):
        self.raw_text = raw_text
        self.name = name
        self.quantity = quantity
        self.unit = unit
        self.matched_unit = matched_unit
        self.estimated_cost = estimated_cost


class IngestionService:
    def __init__(self, session: Session):
        self.session = session
        self.catalog_service = CatalogService(session)
        self.ledger_service = LedgerService(session)

    def parse_natural_language_text(self, text: str) -> list[ParsedIngestionItem]:
        """Parse natural language grocery lists, receipt lines, or garden harvest logs.

        Examples:
        - "2 lbs chicken breast"
        - "500ml milk"
        - "3 apples"
        - "1 cup jasmine rice"
        """
        lines = [line.strip() for line in re.split(r"[\n,;]+", text) if line.strip()]
        results: list[ParsedIngestionItem] = []

        pattern = re.compile(
            r"^(?:(?P<qty>\d+(?:\.\d+)?)\s*)?(?:(?P<unit>[a-zA-Z]+)\s+)?(?P<name>.+)$"
        )

        for line in lines:
            match = pattern.match(line)
            if not match:
                continue

            qty_str = match.group("qty")
            unit_str = match.group("unit")
            name_str = match.group("name").strip()

            quantity = float(qty_str) if qty_str else 1.0
            unit = UnitType.PIECE

            if unit_str and unit_str.lower() in UNIT_SYNONYMS:
                unit = UNIT_SYNONYMS[unit_str.lower()]
            elif unit_str:
                # If unit wasn't recognized, combine it back into the name
                name_str = f"{unit_str} {name_str}".strip()

            # Attempt to match with existing catalog item
            matches = self.catalog_service.search(query=name_str, limit=1)
            matched = matches[0] if matches else None

            cost = (matched.default_cost * quantity) if matched else 0.0

            results.append(
                ParsedIngestionItem(
                    raw_text=line,
                    name=name_str,
                    quantity=quantity,
                    unit=unit,
                    matched_unit=matched,
                    estimated_cost=cost,
                )
            )

        return results

    def ingest_item(
        self,
        intake_unit_id: int,
        quantity: float,
        unit: UnitType,
        storage_location: StorageLocation = StorageLocation.FRIDGE,
        cost_basis: float = 0.0,
        source: str = "grocery",
        shelf_life_days: int | None = None,
        notes: str | None = None,
    ) -> InventoryItem:
        """Acquire an intake unit into inventory and automatically record to ledger."""
        intake_unit = self.catalog_service.get_by_id(intake_unit_id)
        if not intake_unit:
            raise ValueError(f"IntakeUnit #{intake_unit_id} not found.")

        # Compute dynamic expiry based on storage location
        days = shelf_life_days
        if days is None:
            match storage_location:
                case StorageLocation.FRIDGE:
                    days = intake_unit.shelf_life_fridge_days or 7
                case StorageLocation.FREEZER:
                    days = intake_unit.shelf_life_freezer_days or 180
                case StorageLocation.PANTRY | StorageLocation.CABINET:
                    days = intake_unit.shelf_life_pantry_days or 30
                case StorageLocation.COUNTER:
                    days = intake_unit.shelf_life_counter_days or 5

        now = datetime.now(UTC)
        expiry_date = now + timedelta(days=days)

        inv_item = InventoryItem(
            intake_unit_id=intake_unit.id,
            storage_location=storage_location,
            quantity=quantity,
            unit=unit,
            cost_basis=cost_basis,
            acquisition_date=now,
            expiry_date=expiry_date,
            source=source,
            notes=notes,
        )
        self.session.add(inv_item)
        self.session.commit()
        self.session.refresh(inv_item)

        # Record acquisition in cryptographic ledger
        self.ledger_service.record_event(
            event_type=EventType.ACQUIRE,
            intake_unit_id=intake_unit.id,
            quantity=quantity,
            unit=unit,
            cost_delta=cost_basis,
            notes=f"Acquired via {source} -> {storage_location.value}",
        )

        return inv_item
