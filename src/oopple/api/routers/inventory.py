"""API Router for Physical Inventory Lifecycle, Storage Transitions, and Consumption."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from oopple.core.database import get_session
from oopple.domain.enums import StorageLocation, UnitType
from oopple.services.catalog_service import CatalogService
from oopple.services.ingestion_service import IngestionService
from oopple.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["Inventory Lifecycle"])


class IngestItemRequest(BaseModel):
    intake_unit_id: int
    quantity: float
    unit: UnitType
    storage_location: StorageLocation = StorageLocation.FRIDGE
    cost_basis: float = 0.0
    source: str = "grocery"
    shelf_life_days: int | None = None
    notes: str | None = None


class ParseTextRequest(BaseModel):
    text: str


class MoveLocationRequest(BaseModel):
    target_location: StorageLocation


class ConsumeItemRequest(BaseModel):
    quantity: float
    unit: UnitType | None = None
    notes: str | None = None


class WasteItemRequest(BaseModel):
    reason: str = "Expired / Spoiled"


@router.get("")
def list_inventory(
    location: StorageLocation | None = Query(None, description="Filter by location"),
    session: Session = Depends(get_session),
):
    """List stored food, ingredient, and beverage batches with real-time shelf life status."""
    service = InventoryService(session)
    statuses = service.list_inventory(location=location)
    return [
        {
            "id": s.item.id,
            "intake_unit_id": s.item.intake_unit_id,
            "name": s.intake_unit.name,
            "brand": s.intake_unit.brand,
            "category": s.intake_unit.category,
            "cuisine_type": s.intake_unit.cuisine_type,
            "storage_location": s.item.storage_location,
            "quantity": s.item.quantity,
            "unit": s.item.unit,
            "cost_basis": s.item.cost_basis,
            "acquisition_date": s.item.acquisition_date.isoformat(),
            "expiry_date": s.item.expiry_date.isoformat(),
            "days_remaining": s.days_remaining,
            "urgency": s.urgency.value,
            "calories_per_serving": s.intake_unit.calories,
            "protein_per_serving": s.intake_unit.protein_g,
            "source": s.item.source,
            "notes": s.item.notes,
        }
        for s in statuses
    ]


@router.post("/ingest", status_code=201)
def ingest_inventory_item(
    payload: IngestItemRequest,
    session: Session = Depends(get_session),
):
    """Acquire an IntakeUnit into inventory and record the ACQUIRE event to the ledger."""
    service = IngestionService(session)
    try:
        item = service.ingest_item(
            intake_unit_id=payload.intake_unit_id,
            quantity=payload.quantity,
            unit=payload.unit,
            storage_location=payload.storage_location,
            cost_basis=payload.cost_basis,
            source=payload.source,
            shelf_life_days=payload.shelf_life_days,
            notes=payload.notes,
        )
        return {"status": "success", "inventory_item_id": item.id, "message": "Item acquired"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/parse-text")
def parse_ingestion_text(
    payload: ParseTextRequest,
    session: Session = Depends(get_session),
):
    """Parse natural language grocery lists or garden logs before saving."""
    cat_svc = CatalogService(session)
    cat_svc.seed_defaults_if_empty()
    service = IngestionService(session)
    parsed_items = service.parse_natural_language_text(payload.text)
    return [
        {
            "raw_text": p.raw_text,
            "parsed_name": p.name,
            "quantity": p.quantity,
            "unit": p.unit.value,
            "matched_unit_id": p.matched_unit.id if p.matched_unit else None,
            "matched_unit_name": p.matched_unit.name if p.matched_unit else None,
            "estimated_cost": p.estimated_cost,
        }
        for p in parsed_items
    ]


@router.post("/{item_id}/move")
def move_item_location(
    item_id: int,
    payload: MoveLocationRequest,
    session: Session = Depends(get_session),
):
    """Move inventory item between locations (e.g. Fridge -> Freezer) with decay adaptation."""
    service = InventoryService(session)
    try:
        updated = service.move_item_location(item_id, payload.target_location)
        return {
            "status": "success",
            "item_id": updated.id,
            "new_location": updated.storage_location,
            "new_expiry": updated.expiry_date.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{item_id}/consume")
def consume_inventory_item(
    item_id: int,
    payload: ConsumeItemRequest,
    session: Session = Depends(get_session),
):
    """Consume a full or partial quantity of stored inventory and log to nutrition ledger."""
    service = InventoryService(session)
    try:
        remaining_item, consumed_qty = service.consume_item(
            item_id=item_id,
            quantity_to_consume=payload.quantity,
            unit=payload.unit,
            notes=payload.notes,
        )
        return {
            "status": "success",
            "consumed_quantity": consumed_qty,
            "remaining_quantity": remaining_item.quantity if remaining_item else 0.0,
            "is_depleted": remaining_item is None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{item_id}/waste")
def waste_inventory_item(
    item_id: int,
    payload: WasteItemRequest,
    session: Session = Depends(get_session),
):
    """Discard an expired/spoiled inventory batch and log waste loss to ledger."""
    service = InventoryService(session)
    try:
        wasted_cost = service.discard_waste_item(item_id=item_id, reason=payload.reason)
        return {
            "status": "success",
            "wasted_cost_logged": wasted_cost,
            "message": "Item discarded and loss recorded in ledger.",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
