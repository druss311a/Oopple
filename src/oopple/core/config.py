"""Application configuration and constants."""

from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Oopple"
    version: str = "0.1.0"
    db_path: Path = Path("oopple.db")
    openfoodfacts_user_agent: str = "Oopple-NutritionTracker/0.1.0 (contact@oopple.app)"
    default_water_target_ml: float = 2500.0
    default_calorie_target: float = 2000.0
    default_protein_target_g: float = 140.0
    default_carbs_target_g: float = 200.0
    default_fat_target_g: float = 65.0


settings = Settings()
