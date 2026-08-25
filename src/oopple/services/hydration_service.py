"""Hydration Service - managing fluid tracking, pacing, and whole-food water contributions."""

from sqlmodel import Session, select

from oopple.domain.enums import EventType, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.ledger import LedgerEntry
from oopple.domain.user_profile import (
    DEFAULT_WATER_PREFERENCE_KEY,
    DEFAULT_WATER_PREFERENCE_NOTE,
    TastePreference,
    UserProfile,
)
from oopple.services.catalog_service import CatalogService
from oopple.services.ledger_service import LedgerService


class HydrationStatus:
    def __init__(
        self,
        target_ml: float,
        current_ml: float,
        direct_water_ml: float,
        food_water_ml: float,
        percent_achieved: float,
        remaining_ml: float,
        preference_note: str,
    ):
        self.target_ml = round(target_ml, 1)
        self.current_ml = round(current_ml, 1)
        self.direct_water_ml = round(direct_water_ml, 1)
        self.food_water_ml = round(food_water_ml, 1)
        self.percent_achieved = round(percent_achieved, 1)
        self.remaining_ml = round(remaining_ml, 1)
        self.preference_note = preference_note


class HydrationService:
    def __init__(self, session: Session):
        self.session = session
        self.catalog_service = CatalogService(session)
        self.ledger_service = LedgerService(session)

    def ensure_default_user_and_water_preference(self, user_id: int = 1) -> UserProfile:
        """Initialize default user and foundational 'Trust us, your body likes water' preference."""
        user = self.session.get(UserProfile, user_id)
        if not user:
            user = UserProfile(id=user_id, name="Primary User")
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        # Check for default water preference
        pref = self.session.exec(
            select(TastePreference).where(
                TastePreference.user_id == user_id,
                TastePreference.item_or_cuisine_key == DEFAULT_WATER_PREFERENCE_KEY,
            )
        ).first()

        if not pref:
            pref = TastePreference(
                user_id=user_id,
                item_or_cuisine_key=DEFAULT_WATER_PREFERENCE_KEY,
                preference_score=1.0,
                is_favorite=True,
                notes=DEFAULT_WATER_PREFERENCE_NOTE,
            )
            self.session.add(pref)
            self.session.commit()

        return user

    def log_fluid(
        self,
        amount_ml: float,
        source_name: str = "Pure Spring Water",
        notes: str | None = None,
    ) -> LedgerEntry:
        """Quickly log water / hydration intake."""
        self.catalog_service.seed_defaults_if_empty()
        water_unit = self.catalog_service.get_by_sku("OO-WATER-001")
        if not water_unit:
            # Fallback creation
            water_unit = IntakeUnit(
                sku="OO-WATER-001",
                name="Pure Spring Water",
                serving_size=amount_ml,
                serving_unit=UnitType.MILLILITER,
                water_ml=amount_ml,
            )
            self.session.add(water_unit)
            self.session.commit()
            self.session.refresh(water_unit)

        return self.ledger_service.record_event(
            event_type=EventType.HYDRATE,
            intake_unit_id=water_unit.id,
            quantity=amount_ml,
            unit=UnitType.MILLILITER,
            notes=notes or f"Hydration: {source_name}",
        )

    def get_hydration_status(self, user_id: int = 1) -> HydrationStatus:
        """Calculate today's hydration metrics (direct water vs water from food)."""
        user = self.ensure_default_user_and_water_preference(user_id)
        target = user.daily_water_target_ml

        daily = self.ledger_service.get_daily_summary()
        total_water = daily["total_water_ml"]

        # Breakdown between pure hydration vs food water
        # Query today's hydrate entries
        statement = select(LedgerEntry).where(LedgerEntry.event_type == EventType.HYDRATE)
        hydrate_entries = list(self.session.exec(statement).all())
        direct_water = sum(e.delta_water_ml for e in hydrate_entries)
        food_water = max(0.0, total_water - direct_water)

        pct = (total_water / target * 100.0) if target > 0 else 0.0
        remaining = max(0.0, target - total_water)

        return HydrationStatus(
            target_ml=target,
            current_ml=total_water,
            direct_water_ml=direct_water,
            food_water_ml=food_water,
            percent_achieved=min(200.0, pct),
            remaining_ml=remaining,
            preference_note=DEFAULT_WATER_PREFERENCE_NOTE,
        )
