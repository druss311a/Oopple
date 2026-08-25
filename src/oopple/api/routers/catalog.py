"""API Router for IntakeUnit Catalog and Barcode Discovery."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from oopple.core.database import get_session
from oopple.domain.enums import CuisineType, ItemCategory
from oopple.domain.intake_unit import IntakeUnitCreate, IntakeUnitRead
from oopple.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/catalog", tags=["Catalog & Discovery"])


@router.get("", response_model=list[IntakeUnitRead])
def search_catalog(
    q: str | None = Query(None, description="Search query string"),
    category: ItemCategory | None = Query(None, description="Filter by category"),
    cuisine: CuisineType | None = Query(None, description="Filter by cuisine"),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """Search and discover intake units in the catalog."""
    service = CatalogService(session)
    service.seed_defaults_if_empty()
    return service.search(query=q, category=category, cuisine_type=cuisine, limit=limit)


@router.get("/{unit_id}", response_model=IntakeUnitRead)
def get_intake_unit(unit_id: int, session: Session = Depends(get_session)):
    """Get single intake unit by database ID."""
    service = CatalogService(session)
    unit = service.get_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="IntakeUnit not found")
    return unit


@router.post("", response_model=IntakeUnitRead, status_code=201)
def create_intake_unit(payload: IntakeUnitCreate, session: Session = Depends(get_session)):
    """Create a new custom IntakeUnit."""
    service = CatalogService(session)
    existing = service.get_by_sku(payload.sku)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"IntakeUnit with SKU '{payload.sku}' already exists"
        )
    return service.create_unit(payload)


@router.post("/barcode/{barcode}", response_model=IntakeUnitRead)
async def lookup_barcode(barcode: str, session: Session = Depends(get_session)):
    """Scan / lookup barcode via local cache or OpenFoodFacts API with auto-caching."""
    service = CatalogService(session)
    unit = await service.lookup_or_fetch_barcode(barcode)
    if not unit:
        raise HTTPException(
            status_code=404,
            detail=f"Product with barcode '{barcode}' not found in local catalog or OpenFoodFacts.",
        )
    return unit
