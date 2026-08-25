"""Recipe and culinary composition domain models."""

from sqlmodel import Field, Relationship, SQLModel

from oopple.domain.enums import CuisineType, UnitType
from oopple.domain.intake_unit import IntakeUnit


class RecipeIngredientBase(SQLModel):
    recipe_id: int | None = Field(default=None, foreign_key="recipes.id", index=True)
    intake_unit_id: int = Field(foreign_key="intake_units.id", index=True)
    quantity: float = Field(default=1.0, gt=0.0)
    unit: UnitType = Field(default=UnitType.GRAM)
    is_optional: bool = Field(default=False)
    substitutes: str | None = Field(
        default=None,
        description="Comma-separated substitute intake unit SKUs",
    )


class RecipeIngredient(RecipeIngredientBase, table=True):
    __tablename__ = "recipe_ingredients"

    id: int | None = Field(default=None, primary_key=True)
    recipe: "Recipe" | None = Relationship(back_populates="ingredients")
    intake_unit: IntakeUnit | None = Relationship()


class RecipeBase(SQLModel):
    name: str = Field(index=True)
    description: str | None = Field(default=None)
    cuisine_type: CuisineType = Field(default=CuisineType.GLOBAL, index=True)
    prep_time_minutes: int = Field(default=15, ge=0)
    cook_time_minutes: int = Field(default=20, ge=0)
    servings: int = Field(default=2, gt=0)
    instructions: str = Field(default="", description="Preparation steps")
    tags: str = Field(default="")


class Recipe(RecipeBase, table=True):
    __tablename__ = "recipes"

    id: int | None = Field(default=None, primary_key=True)
    ingredients: list[RecipeIngredient] = Relationship(back_populates="recipe")


class RecipeRead(RecipeBase):
    id: int
    ingredients: list[RecipeIngredient] = []
