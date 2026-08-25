"""Main FastAPI Application Entrypoint for Oopple."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from oopple.api.routers import catalog, hydration, inventory, ledger, recipes, user
from oopple.core.config import settings
from oopple.core.database import engine, init_db
from oopple.services.catalog_service import CatalogService
from oopple.services.hydration_service import HydrationService
from oopple.services.optimizer_service import OptimizerService

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown lifecycle: initializes schema and seeds foundational data."""
    init_db()
    with Session(engine) as session:
        cat_svc = CatalogService(session)
        cat_svc.seed_defaults_if_empty()

        opt_svc = OptimizerService(session)
        opt_svc.seed_recipes_if_empty()

        hyd_svc = HydrationService(session)
        hyd_svc.ensure_default_user_and_water_preference()
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version=settings.version,
    description="Intelligent Nutrition, Inventory, Hydration & Culinary Optimization Platform",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(recipes.router)
app.include_router(hydration.router)
app.include_router(ledger.router)
app.include_router(user.router)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def read_root():
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"status": "ok", "app": settings.app_name, "version": settings.version}
