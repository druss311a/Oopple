"""API Router for Recipes and Multi-Objective Expiry Optimizer."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from oopple.core.database import get_session
from oopple.domain.intake_unit import IntakeUnit
from oopple.domain.recipe import RecipeIngredient
from oopple.services.optimizer_service import OptimizerService

router = APIRouter(tags=["Recipes & Optimizer"])


class CookRecipeRequest(BaseModel):
    recipe_id: int
    portions: float = 1.0
    notes: str | None = None


@router.get("/api/recipes")
def list_recipes(session: Session = Depends(get_session)):
    """List all recipes in the culinary database."""
    service = OptimizerService(session)
    service.seed_recipes_if_empty()
    recipes = service.list_recipes()
    results = []
    for r in recipes:
        ingredients = list(
            session.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == r.id).all()
        )
        ing_details = []
        for ing in ingredients:
            unit = session.get(IntakeUnit, ing.intake_unit_id)
            ing_details.append(
                {
                    "intake_unit_id": ing.intake_unit_id,
                    "name": unit.name if unit else "Unknown",
                    "quantity": ing.quantity,
                    "unit": ing.unit.value,
                    "is_optional": ing.is_optional,
                }
            )
        results.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "cuisine_type": r.cuisine_type.value,
                "prep_time_minutes": r.prep_time_minutes,
                "cook_time_minutes": r.cook_time_minutes,
                "servings": r.servings,
                "instructions": r.instructions,
                "tags": r.tags,
                "ingredients": ing_details,
            }
        )
    return results


@router.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    """Get single recipe with full ingredient list."""
    service = OptimizerService(session)
    recipe = service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.get("/api/optimizer/suggest")
def suggest_meals(
    user_id: int = Query(1, description="User profile ID"),
    weight_expiry: float = Query(3.5, description="Weight for near-expiring ingredients"),
    weight_inventory: float = Query(3.0, description="Weight for on-hand stock"),
    weight_nutrition: float = Query(2.0, description="Weight for macro/calorie goal fulfillment"),
    weight_preference: float = Query(1.5, description="Weight for cuisine preferences"),
    session: Session = Depends(get_session),
):
    """Run optimizer: recommends recipes prioritizing expiring food and macro fit."""
    service = OptimizerService(session)
    service.seed_recipes_if_empty()
    recommendations = service.suggest_meals(
        user_id=user_id,
        weight_expiry=weight_expiry,
        weight_inventory=weight_inventory,
        weight_nutrition=weight_nutrition,
        weight_preference=weight_preference,
    )
    return [
        {
            "recipe_id": rec.recipe.id,
            "recipe_name": rec.recipe.name,
            "cuisine_type": rec.recipe.cuisine_type.value,
            "score": rec.score,
            "inventory_match_ratio": rec.inventory_match_ratio,
            "expiring_ingredients_used": rec.expiring_ingredients_used,
            "missing_ingredients": rec.missing_ingredients,
            "total_calories": rec.total_calories,
            "total_protein_g": rec.total_protein_g,
            "total_carbs_g": rec.total_carbs_g,
            "total_fat_g": rec.total_fat_g,
            "estimated_cost": rec.estimated_cost,
            "prep_time_minutes": rec.recipe.prep_time_minutes,
            "cook_time_minutes": rec.recipe.cook_time_minutes,
        }
        for rec in recommendations
    ]


@router.post("/api/optimizer/cook")
def cook_recipe(payload: CookRecipeRequest, session: Session = Depends(get_session)):
    """Cook a recipe: deducts ingredients from oldest inventory batches and logs meal to ledger."""
    service = OptimizerService(session)
    try:
        consumed_log = service.cook_and_consume_recipe(
            recipe_id=payload.recipe_id,
            portions=payload.portions,
            notes=payload.notes,
        )
        return {
            "status": "success",
            "recipe_id": payload.recipe_id,
            "portions": payload.portions,
            "deducted_batches_count": len(consumed_log),
            "message": "Meal logged to nutrition ledger and inventory updated.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
