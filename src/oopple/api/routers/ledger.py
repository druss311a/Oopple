"""API Router for Cryptographic Nutrition & Cost Ledger Audit Trail."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, col, select

from oopple.core.database import get_session
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.ledger import LedgerEntry
from oopple.services.ledger_service import LedgerService

router = APIRouter(prefix="/api/ledger", tags=["Nutrition & Cost Ledger"])


@router.get("/entries")
def list_ledger_entries(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Retrieve chronological ledger blocks with SHA-256 hashes and nutritional deltas."""
    statement = (
        select(LedgerEntry)
        .order_by(col(LedgerEntry.sequence_number).desc())
        .offset(offset)
        .limit(limit)
    )
    entries = list(session.exec(statement).all())
    results = []
    for e in entries:
        unit = session.get(IntakeUnit, e.intake_unit_id)
        results.append(
            {
                "sequence_number": e.sequence_number,
                "prev_hash": e.prev_hash,
                "current_hash": e.current_hash,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "intake_unit_name": unit.name if unit else "Unknown",
                "quantity": e.quantity,
                "unit": e.unit.value,
                "delta_calories": e.delta_calories,
                "delta_protein_g": e.delta_protein_g,
                "delta_carbs_g": e.delta_carbs_g,
                "delta_fat_g": e.delta_fat_g,
                "delta_water_ml": e.delta_water_ml,
                "cost_delta": e.cost_delta,
                "notes": e.notes,
            }
        )
    return results


@router.get("/summary")
def get_daily_summary(
    target_date: date | None = Query(None, description="Date for aggregate metrics (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
):
    """Get aggregate nutrition, hydration, and expenditure/waste stats for the day."""
    service = LedgerService(session)
    return service.get_daily_summary(target_date=target_date)


@router.get("/verify")
def verify_ledger(session: Session = Depends(get_session)):
    """Run cryptographic validation on the entire ledger hash chain."""
    service = LedgerService(session)
    valid, message = service.verify_ledger_integrity()
    return {
        "is_valid": valid,
        "message": message,
    }
