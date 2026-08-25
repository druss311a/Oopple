"""Seed recipes linking with fundamental IntakeUnits."""

from oopple.domain.enums import CuisineType, UnitType

SEED_RECIPES = [
    {
        "name": "Mediterranean Lemon Chicken & Spinach",
        "description": "Pan-seared chicken breast atop warm garlicky sautéed baby spinach.",
        "cuisine_type": CuisineType.MEDITERRANEAN,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 2,
        "instructions": (
            "1. Season chicken breast with salt, pepper, and herbs.\n"
            "2. Heat olive oil in a skillet over medium-high heat.\n"
            "3. Sear chicken for 6-7 min per side until 165°F.\n"
            "4. Toss fresh baby spinach in pan until wilted.\n"
            "5. Plate chicken over spinach, drizzle juices, and serve."
        ),
        "tags": "high-protein,low-carb,mediterranean,quick",
        "ingredients": [
            {
                "sku": "OO-CHICKEN-001",
                "quantity": 300.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-SPINACH-001",
                "quantity": 150.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-OLIVEOIL-001",
                "quantity": 15.0,
                "unit": UnitType.MILLILITER,
                "is_optional": False,
            },
        ],
    },
    {
        "name": "Atlantic Salmon with Steamed Jasmine Rice",
        "description": "Crispy skin Atlantic salmon fillet paired with steamed jasmine rice.",
        "cuisine_type": CuisineType.NORDIC,
        "prep_time_minutes": 5,
        "cook_time_minutes": 15,
        "servings": 1,
        "instructions": (
            "1. Rinse and steam jasmine rice.\n"
            "2. Pat salmon dry and season with sea salt.\n"
            "3. Heat olive oil in skillet on medium-high.\n"
            "4. Sear salmon skin-side down for 4 min, flip and cook 3 min.\n"
            "5. Serve over steamed jasmine rice."
        ),
        "tags": "omega3,seafood,balanced,clean-eating",
        "ingredients": [
            {
                "sku": "OO-SALMON-001",
                "quantity": 180.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-RICE-001",
                "quantity": 80.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-OLIVEOIL-001",
                "quantity": 10.0,
                "unit": UnitType.MILLILITER,
                "is_optional": True,
            },
        ],
    },
    {
        "name": "Morning Protein Power Scramble",
        "description": "Fluffy eggs scrambled with baby spinach and cold-pressed olive oil.",
        "cuisine_type": CuisineType.GLOBAL,
        "prep_time_minutes": 5,
        "cook_time_minutes": 5,
        "servings": 1,
        "instructions": (
            "1. Whisk eggs in a bowl with salt.\n"
            "2. Heat olive oil in a skillet on medium-low.\n"
            "3. Add spinach and let wilt for 1 minute.\n"
            "4. Pour in eggs and gently fold until softly set.\n"
            "5. Serve immediately."
        ),
        "tags": "breakfast,keto,fast,protein",
        "ingredients": [
            {
                "sku": "OO-EGGS-001",
                "quantity": 3.0,
                "unit": UnitType.PIECE,
                "is_optional": False,
            },
            {
                "sku": "OO-SPINACH-001",
                "quantity": 50.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-OLIVEOIL-001",
                "quantity": 5.0,
                "unit": UnitType.MILLILITER,
                "is_optional": False,
            },
        ],
    },
    {
        "name": "Greek Yogurt Crisp Apple & Honey Parfait",
        "description": "Thick probiotic Greek yogurt topped with diced Honeycrisp apple.",
        "cuisine_type": CuisineType.MEDITERRANEAN,
        "prep_time_minutes": 3,
        "cook_time_minutes": 0,
        "servings": 1,
        "instructions": (
            "1. Spoon Greek yogurt into a bowl.\n"
            "2. Dice Honeycrisp apple into bite-sized cubes.\n"
            "3. Layer apples over yogurt and enjoy chilled."
        ),
        "tags": "snack,no-cook,vegetarian,gut-health",
        "ingredients": [
            {
                "sku": "OO-YOGURT-001",
                "quantity": 200.0,
                "unit": UnitType.GRAM,
                "is_optional": False,
            },
            {
                "sku": "OO-APPLE-001",
                "quantity": 1.0,
                "unit": UnitType.PIECE,
                "is_optional": False,
            },
        ],
    },
]
