"""Catalog Service - managing IntakeUnit discovery, OpenFoodFacts lookups, and local caching."""

import httpx
from sqlmodel import Session, col, or_, select

from oopple.core.config import settings
from oopple.domain.enums import CuisineType, ItemCategory, UnitType
from oopple.domain.intake_unit import IntakeUnit, IntakeUnitCreate
from oopple.services.catalog_seeds import SEED_INTAKE_UNITS


class CatalogService:
    def __init__(self, session: Session):
        self.session = session

    def seed_defaults_if_empty(self) -> int:
        """Populate base foods, staples, and hydration units if catalog is empty."""
        count = len(list(self.session.exec(select(IntakeUnit)).all()))
        if count > 0:
            return 0

        inserted = 0
        for item_data in SEED_INTAKE_UNITS:
            unit = IntakeUnit(**item_data)
            self.session.add(unit)
            inserted += 1
        self.session.commit()
        return inserted

    def get_by_id(self, unit_id: int) -> IntakeUnit | None:
        """Fetch an intake unit by database ID."""
        return self.session.get(IntakeUnit, unit_id)

    def get_by_sku(self, sku: str) -> IntakeUnit | None:
        """Fetch an intake unit by SKU."""
        statement = select(IntakeUnit).where(IntakeUnit.sku == sku)
        return self.session.exec(statement).first()

    def get_by_barcode(self, barcode: str) -> IntakeUnit | None:
        """Fetch an intake unit by barcode from local DB."""
        clean_code = barcode.strip()
        statement = select(IntakeUnit).where(IntakeUnit.barcode == clean_code)
        return self.session.exec(statement).first()

    def search(
        self,
        query: str | None = None,
        category: ItemCategory | None = None,
        cuisine_type: CuisineType | None = None,
        limit: int = 50,
    ) -> list[IntakeUnit]:
        """Search catalog by query string, category, or cuisine."""
        statement = select(IntakeUnit)

        if category:
            statement = statement.where(IntakeUnit.category == category)
        if cuisine_type:
            statement = statement.where(IntakeUnit.cuisine_type == cuisine_type)

        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    col(IntakeUnit.name).ilike(term),
                    col(IntakeUnit.brand).ilike(term),
                    col(IntakeUnit.sku).ilike(term),
                    col(IntakeUnit.tags).ilike(term),
                )
            )

        statement = statement.limit(limit)
        return list(self.session.exec(statement).all())

    def create_unit(self, unit_create: IntakeUnitCreate) -> IntakeUnit:
        """Create a custom or newly discovered intake unit."""
        unit = IntakeUnit.model_validate(unit_create)
        self.session.add(unit)
        self.session.commit()
        self.session.refresh(unit)
        return unit

    async def lookup_or_fetch_barcode(
        self,
        barcode: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> IntakeUnit | None:
        """Find item locally, or query OpenFoodFacts API and cache the result."""
        clean_code = barcode.strip()
        local_unit = self.get_by_barcode(clean_code)
        if local_unit:
            return local_unit

        # Query OpenFoodFacts API
        url = f"https://world.openfoodfacts.org/api/v2/product/{clean_code}.json"
        headers = {"User-Agent": settings.openfoodfacts_user_agent}

        try:
            if http_client:
                response = await http_client.get(url, headers=headers, timeout=5.0)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=5.0)

            if response.status_code != 200:
                return None

            data = response.json()
            if data.get("status") != 1:
                return None

            product = data.get("product", {})
            product_name = (
                product.get("product_name")
                or product.get("generic_name")
                or f"Product {clean_code}"
            )
            brand = product.get("brands") or "Generic"
            nutriments = product.get("nutriments", {})

            # Extract nutritional facts (per 100g base)
            calories = float(
                nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0.0
            )
            protein = float(nutriments.get("proteins_100g") or 0.0)
            carbs = float(nutriments.get("carbohydrates_100g") or 0.0)
            fat = float(nutriments.get("fat_100g") or 0.0)
            fiber = float(nutriments.get("fiber_100g") or 0.0)
            sodium = float(nutriments.get("sodium_100g") or 0.0) * 1000.0  # Convert g to mg
            water = float(nutriments.get("water_100g") or 0.0)

            sku = f"OFF-{clean_code}"
            # Avoid duplicate SKU collisions
            if self.get_by_sku(sku):
                sku = f"OFF-{clean_code}-AUTO"

            new_unit = IntakeUnit(
                sku=sku,
                name=product_name,
                brand=brand,
                barcode=clean_code,
                cuisine_type=CuisineType.GLOBAL,
                category=ItemCategory.PREPARED,
                serving_size=100.0,
                serving_unit=UnitType.GRAM,
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                fiber_g=fiber,
                sodium_mg=sodium,
                water_ml=water,
                shelf_life_pantry_days=60,
                default_cost=2.99,
                tags="barcode_scan,openfoodfacts",
            )
            self.session.add(new_unit)
            self.session.commit()
            self.session.refresh(new_unit)
            return new_unit
        except Exception:
            return None
