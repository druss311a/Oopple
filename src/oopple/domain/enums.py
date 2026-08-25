"""Domain enumerations for Oopple."""

from enum import StrEnum


class StorageLocation(StrEnum):
    FRIDGE = "fridge"
    FREEZER = "freezer"
    PANTRY = "pantry"
    CABINET = "cabinet"
    COUNTER = "counter"


class EventType(StrEnum):
    ACQUIRE = "acquire"
    STORE = "store"
    TRANSFORM_PREP = "transform_prep"
    CONSUME = "consume"
    HYDRATE = "hydrate"
    WASTE_DISCARD = "waste_discard"
    ADJUST = "adjust"


class CuisineType(StrEnum):
    AMERICANA = "americana"
    MEDITERRANEAN = "mediterranean"
    ASIAN = "asian"
    LATIN = "latin"
    ITALIAN = "italian"
    MIDDLE_EASTERN = "middle_eastern"
    NORDIC = "nordic"
    GLOBAL = "global"
    BEVERAGE = "beverage"


class ItemCategory(StrEnum):
    PRODUCE = "produce"
    PROTEIN = "protein"
    DAIRY = "dairy"
    GRAIN = "grain"
    BEVERAGE = "beverage"
    SPICE = "spice"
    CONDIMENT = "condiment"
    BAKERY = "bakery"
    SNACK = "snack"
    PREPARED = "prepared"


class UnitType(StrEnum):
    GRAM = "g"
    MILLILITER = "ml"
    PIECE = "piece"
    OUNCE = "oz"
    POUND = "lb"
    CUP = "cup"
    TABLESPOON = "tbsp"
    TEASPOON = "tsp"
    SERVING = "serving"


class ExpiryUrgency(StrEnum):
    CRITICAL_TODAY = "critical_today"  # Expiring <= 1 day
    USE_SOON = "use_soon"  # Expiring <= 3 days
    FRESH = "fresh"  # Expiring > 3 days
    EXPIRED = "expired"  # Expired (< 0 days)
    SHELF_STABLE = "shelf_stable"  # No realistic expiry
