"""User Profile, Nutritional Target Goals, and Taste Preference domain models."""

from sqlmodel import Field, SQLModel


class UserProfileBase(SQLModel):
    name: str = Field(default="Default User")
    daily_calories_target: float = Field(default=2000.0)
    daily_protein_target_g: float = Field(default=140.0)
    daily_carbs_target_g: float = Field(default=200.0)
    daily_fat_target_g: float = Field(default=65.0)
    daily_fiber_target_g: float = Field(default=30.0)
    daily_sodium_max_mg: float = Field(default=2300.0)
    daily_water_target_ml: float = Field(default=2500.0, description="Daily hydration target")
    weekly_grocery_budget: float = Field(default=120.0, description="Target budget in dollars")


class UserProfile(UserProfileBase, table=True):
    __tablename__ = "user_profiles"

    id: int | None = Field(default=None, primary_key=True)


class TastePreferenceBase(SQLModel):
    user_id: int = Field(default=1, foreign_key="user_profiles.id", index=True)
    item_or_cuisine_key: str = Field(index=True, description="SKU, cuisine name, or category")
    preference_score: float = Field(
        default=1.0,
        ge=-1.0,
        le=1.0,
        description="-1.0 (dislike) to +1.0 (love), 0.0 is neutral",
    )
    is_favorite: bool = Field(default=False)
    notes: str | None = Field(default=None)


class TastePreference(TastePreferenceBase, table=True):
    __tablename__ = "taste_preferences"

    id: int | None = Field(default=None, primary_key=True)


DEFAULT_WATER_PREFERENCE_KEY = "OO-WATER-001"
DEFAULT_WATER_PREFERENCE_NOTE = "Trust us, your body likes water."
