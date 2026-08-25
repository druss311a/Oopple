"""API Router for User Profile, Targets, and Taste Preferences."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from oopple.core.database import get_session
from oopple.domain.user_profile import TastePreference
from oopple.services.hydration_service import HydrationService

router = APIRouter(prefix="/api/user", tags=["User Profile & Preferences"])


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    daily_calories_target: float | None = None
    daily_protein_target_g: float | None = None
    daily_carbs_target_g: float | None = None
    daily_fat_target_g: float | None = None
    daily_water_target_ml: float | None = None
    weekly_grocery_budget: float | None = None


class SetPreferenceRequest(BaseModel):
    item_or_cuisine_key: str
    preference_score: float = Field(..., ge=-1.0, le=1.0)
    is_favorite: bool = False
    notes: str | None = None


@router.get("/profile")
def get_user_profile(
    user_id: int = Query(1, description="User ID"),
    session: Session = Depends(get_session),
):
    """Retrieve user nutritional targets, budget, and hydration settings."""
    hydration_svc = HydrationService(session)
    return hydration_svc.ensure_default_user_and_water_preference(user_id=user_id)


@router.put("/profile")
def update_user_profile(
    payload: UpdateProfileRequest,
    user_id: int = Query(1, description="User ID"),
    session: Session = Depends(get_session),
):
    """Update nutritional macro goals, daily water target, or budget."""
    hydration_svc = HydrationService(session)
    user = hydration_svc.ensure_default_user_and_water_preference(user_id=user_id)

    if payload.name is not None:
        user.name = payload.name
    if payload.daily_calories_target is not None:
        user.daily_calories_target = payload.daily_calories_target
    if payload.daily_protein_target_g is not None:
        user.daily_protein_target_g = payload.daily_protein_target_g
    if payload.daily_carbs_target_g is not None:
        user.daily_carbs_target_g = payload.daily_carbs_target_g
    if payload.daily_fat_target_g is not None:
        user.daily_fat_target_g = payload.daily_fat_target_g
    if payload.daily_water_target_ml is not None:
        user.daily_water_target_ml = payload.daily_water_target_ml
    if payload.weekly_grocery_budget is not None:
        user.weekly_grocery_budget = payload.weekly_grocery_budget

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/preferences")
def list_preferences(
    user_id: int = Query(1, description="User ID"),
    session: Session = Depends(get_session),
):
    """List all registered taste preferences (including default water preference)."""
    hydration_svc = HydrationService(session)
    hydration_svc.ensure_default_user_and_water_preference(user_id=user_id)
    statement = select(TastePreference).where(TastePreference.user_id == user_id)
    return list(session.exec(statement).all())


@router.post("/preferences")
def set_preference(
    payload: SetPreferenceRequest,
    user_id: int = Query(1, description="User ID"),
    session: Session = Depends(get_session),
):
    """Set or update user taste affinity for a cuisine, food item, or category."""
    clean_key = payload.item_or_cuisine_key.strip().lower()
    existing = session.exec(
        select(TastePreference).where(
            TastePreference.user_id == user_id,
            TastePreference.item_or_cuisine_key == clean_key,
        )
    ).first()

    if existing:
        existing.preference_score = payload.preference_score
        existing.is_favorite = payload.is_favorite
        existing.notes = payload.notes
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    pref = TastePreference(
        user_id=user_id,
        item_or_cuisine_key=clean_key,
        preference_score=payload.preference_score,
        is_favorite=payload.is_favorite,
        notes=payload.notes,
    )
    session.add(pref)
    session.commit()
    session.refresh(pref)
    return pref
