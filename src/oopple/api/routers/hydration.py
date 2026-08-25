"""API Router for Hydration Tracking and Body Fluid Balance."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from oopple.core.database import get_session
from oopple.services.hydration_service import HydrationService

router = APIRouter(prefix="/api/hydration", tags=["Hydration Tracking"])


class LogFluidRequest(BaseModel):
    amount_ml: float = Field(..., gt=0.0, description="Volume of fluid consumed in milliliters")
    source_name: str = Field(default="Pure Spring Water", description="Source description")
    notes: str | None = Field(default=None)


@router.get("/status")
def get_hydration_status(
    user_id: int = Query(1, description="User profile ID"),
    session: Session = Depends(get_session),
):
    """Get hydration status, breakdown of direct vs food water, and target progress."""
    service = HydrationService(session)
    status = service.get_hydration_status(user_id=user_id)
    return {
        "target_ml": status.target_ml,
        "current_ml": status.current_ml,
        "direct_water_ml": status.direct_water_ml,
        "food_water_ml": status.food_water_ml,
        "percent_achieved": status.percent_achieved,
        "remaining_ml": status.remaining_ml,
        "preference_note": status.preference_note,
    }


@router.post("/log", status_code=201)
def log_fluid_intake(
    payload: LogFluidRequest,
    session: Session = Depends(get_session),
):
    """Quick log hydration intake to the immutable ledger."""
    service = HydrationService(session)
    entry = service.log_fluid(
        amount_ml=payload.amount_ml,
        source_name=payload.source_name,
        notes=payload.notes,
    )
    return {
        "status": "success",
        "ledger_sequence": entry.sequence_number,
        "delta_water_ml": entry.delta_water_ml,
        "current_hash": entry.current_hash,
    }
