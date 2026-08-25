"""Optimizer Service - Multi-objective culinary solver for expiry, nutrition, cost, and taste."""

from sqlmodel import Session, col, select

from oopple.domain.enums import ExpiryUrgency, UnitType
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.inventory import InventoryItem
from oopple.domain.recipe import Recipe, RecipeIngredient
from oopple.domain.units import convert_quantity
from oopple.domain.user_profile import TastePreference, UserProfile
from oopple.services.inventory_service import InventoryService
from oopple.services.ledger_service import LedgerService
from oopple.services.recipe_seeds import SEED_RECIPES


class RecipeRecommendation:
    def __init__(
        self,
        recipe: Recipe,
        score: float,
        inventory_match_ratio: float,
        expiring_ingredients_used: list[str],
        missing_ingredients: list[dict],
        total_calories: float,
        total_protein_g: float,
        total_carbs_g: float,
        total_fat_g: float,
        estimated_cost: float,
    ):
        self.recipe = recipe
        self.score = round(score, 2)
        self.inventory_match_ratio = round(inventory_match_ratio, 2)
        self.expiring_ingredients_used = expiring_ingredients_used
        self.missing_ingredients = missing_ingredients
        self.total_calories = round(total_calories, 1)
        self.total_protein_g = round(total_protein_g, 1)
        self.total_carbs_g = round(total_carbs_g, 1)
        self.total_fat_g = round(total_fat_g, 1)
        self.estimated_cost = round(estimated_cost, 2)


class OptimizerService:
    def __init__(self, session: Session):
        self.session = session
        self.inventory_service = InventoryService(session)
        self.ledger_service = LedgerService(session)

    def seed_recipes_if_empty(self) -> int:
        """Seed foundational recipes if table is empty."""
        count = len(list(self.session.exec(select(Recipe)).all()))
        if count > 0:
            return 0

        inserted = 0
        for r_data in SEED_RECIPES:
            recipe = Recipe(
                name=r_data["name"],
                description=r_data["description"],
                cuisine_type=r_data["cuisine_type"],
                prep_time_minutes=r_data["prep_time_minutes"],
                cook_time_minutes=r_data["cook_time_minutes"],
                servings=r_data["servings"],
                instructions=r_data["instructions"],
                tags=r_data["tags"],
            )
            self.session.add(recipe)
            self.session.commit()
            self.session.refresh(recipe)

            for ing_data in r_data["ingredients"]:
                intake_unit = self.session.exec(
                    select(IntakeUnit).where(IntakeUnit.sku == ing_data["sku"])
                ).first()
                if intake_unit:
                    ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        intake_unit_id=intake_unit.id,
                        quantity=ing_data["quantity"],
                        unit=ing_data["unit"],
                        is_optional=ing_data.get("is_optional", False),
                    )
                    self.session.add(ingredient)
            inserted += 1
        self.session.commit()
        return inserted

    def list_recipes(self) -> list[Recipe]:
        """List all recipes in catalog."""
        return list(self.session.exec(select(Recipe)).all())

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        """Get recipe by ID with its ingredients."""
        return self.session.get(Recipe, recipe_id)

    def suggest_meals(
        self,
        user_id: int = 1,
        weight_expiry: float = 3.5,
        weight_inventory: float = 3.0,
        weight_nutrition: float = 2.0,
        weight_preference: float = 1.5,
    ) -> list[RecipeRecommendation]:
        """Multi-objective optimizer: recommends recipes balancing expiry, stock, macros, taste."""
        recipes = self.list_recipes()
        if not recipes:
            return []

        # Get active inventory items with expiry urgency
        inv_statuses = self.inventory_service.list_inventory()
        # Map intake_unit_id -> list of InventoryItemStatus
        inv_by_unit: dict[int, list] = {}
        for s in inv_statuses:
            inv_by_unit.setdefault(s.item.intake_unit_id, []).append(s)

        # Get user preferences
        prefs = list(
            self.session.exec(
                select(TastePreference).where(TastePreference.user_id == user_id)
            ).all()
        )
        pref_map = {p.item_or_cuisine_key.lower(): p.preference_score for p in prefs}

        # Daily summary for nutrition gap
        daily_summary = self.ledger_service.get_daily_summary()
        cals_consumed = daily_summary["total_calories"]
        protein_consumed = daily_summary["total_protein_g"]

        # Default targets
        user = self.session.get(UserProfile, user_id)
        cal_target = user.daily_calories_target if user else 2000.0
        prot_target = user.daily_protein_target_g if user else 140.0

        cal_remaining = max(0.0, cal_target - cals_consumed)
        prot_remaining = max(0.0, prot_target - protein_consumed)

        recommendations: list[RecipeRecommendation] = []

        for recipe in recipes:
            ingredients = list(
                self.session.exec(
                    select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
                ).all()
            )
            if not ingredients:
                continue

            total_cals = 0.0
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            est_cost = 0.0

            matched_count = 0
            expiring_used: list[str] = []
            missing: list[dict] = []

            for ing in ingredients:
                unit = self.session.get(IntakeUnit, ing.intake_unit_id)
                if not unit:
                    continue

                # Calculate nutritional contribution
                ratio = 1.0
                if unit.serving_size > 0:
                    is_g = unit.serving_unit == UnitType.GRAM
                    is_ml = unit.serving_unit == UnitType.MILLILITER
                    norm_qty = convert_quantity(
                        ing.quantity,
                        ing.unit,
                        unit.serving_unit,
                        serving_mass_g=unit.serving_size if is_g else None,
                        serving_volume_ml=unit.serving_size if is_ml else None,
                    )
                    ratio = norm_qty / unit.serving_size

                total_cals += unit.calories * ratio
                total_protein += unit.protein_g * ratio
                total_carbs += unit.carbs_g * ratio
                total_fat += unit.fat_g * ratio
                est_cost += unit.default_cost * (ing.quantity / max(1.0, unit.serving_size))

                # Check inventory matching
                available_batches = inv_by_unit.get(unit.id, [])
                total_on_hand = sum(
                    convert_quantity(b.item.quantity, b.item.unit, ing.unit)
                    for b in available_batches
                )

                if total_on_hand >= ing.quantity:
                    matched_count += 1
                else:
                    if not ing.is_optional:
                        missing.append(
                            {
                                "name": unit.name,
                                "required": ing.quantity,
                                "on_hand": total_on_hand,
                                "unit": ing.unit.value,
                            }
                        )

                # Check if any on-hand batch is expiring soon
                for b in available_batches:
                    if b.urgency in (ExpiryUrgency.CRITICAL_TODAY, ExpiryUrgency.USE_SOON):
                        if unit.name not in expiring_used:
                            expiring_used.append(f"{unit.name} ({b.urgency.value})")

            match_ratio = matched_count / len(ingredients)

            # Score components
            # 1. Expiry score: 10 points per expiring item utilized
            expiry_score = len(expiring_used) * 10.0

            # 2. Inventory score: 100 * match_ratio
            inv_score = match_ratio * 100.0

            # 3. Nutrition fit: rewards recipes that fulfill remaining protein and calorie goals
            nutri_score = 0.0
            if prot_remaining > 0 and total_protein > 0:
                nutri_score += min(50.0, (total_protein / prot_remaining) * 50.0)
            if cal_remaining > 0 and total_cals > 0:
                nutri_score += max(0.0, 50.0 - abs(total_cals - (cal_remaining / 2)) * 0.1)

            # 4. Preference score
            cuisine_pref = pref_map.get(recipe.cuisine_type.value.lower(), 0.0)
            pref_score = 50.0 + (cuisine_pref * 50.0)

            total_score = (
                (weight_expiry * expiry_score)
                + (weight_inventory * inv_score)
                + (weight_nutrition * nutri_score)
                + (weight_preference * pref_score)
            )

            rec = RecipeRecommendation(
                recipe=recipe,
                score=total_score,
                inventory_match_ratio=match_ratio,
                expiring_ingredients_used=expiring_used,
                missing_ingredients=missing,
                total_calories=total_cals,
                total_protein_g=total_protein,
                total_carbs_g=total_carbs,
                total_fat_g=total_fat,
                estimated_cost=est_cost,
            )
            recommendations.append(rec)

        # Sort recommendations by highest score first
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations

    def cook_and_consume_recipe(
        self,
        recipe_id: int,
        portions: float = 1.0,
        notes: str | None = None,
    ) -> list[tuple[int, float]]:
        """Deduct ingredients from earliest-expiring inventory and log consumption to ledger."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe #{recipe_id} not found.")

        ingredients = list(
            self.session.exec(
                select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
            ).all()
        )

        consumed_log: list[tuple[int, float]] = []

        for ing in ingredients:
            target_qty = ing.quantity * (portions / max(1, recipe.servings))

            # Query available inventory ordered by expiry date (earliest first)
            batches = list(
                self.session.exec(
                    select(InventoryItem)
                    .where(InventoryItem.intake_unit_id == ing.intake_unit_id)
                    .order_by(col(InventoryItem.expiry_date).asc())
                ).all()
            )

            needed = target_qty
            for batch in batches:
                if needed <= 0.001:
                    break

                batch_qty_in_ing_unit = convert_quantity(batch.quantity, batch.unit, ing.unit)
                deduct_qty_ing_unit = min(needed, batch_qty_in_ing_unit)

                self.inventory_service.consume_item(
                    item_id=batch.id,
                    quantity_to_consume=deduct_qty_ing_unit,
                    unit=ing.unit,
                    notes=f"Cooked in recipe '{recipe.name}'",
                )

                needed -= deduct_qty_ing_unit
                consumed_log.append((ing.intake_unit_id, deduct_qty_ing_unit))

        return consumed_log
