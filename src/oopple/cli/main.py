"""Oopple CLI - Terminal command center powered by Typer and Rich."""

import asyncio
import sys

import typer
import uvicorn
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlmodel import Session

from oopple.core.database import engine, init_db
from oopple.domain.enums import StorageLocation
from oopple.services.catalog_service import CatalogService
from oopple.services.hydration_service import HydrationService
from oopple.services.ingestion_service import IngestionService
from oopple.services.inventory_service import InventoryService
from oopple.services.ledger_service import LedgerService
from oopple.services.optimizer_service import OptimizerService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="oopple",
    help="Oopple - Intelligent Nutrition, Inventory Lifecycle & Culinary Engine",
    add_completion=False,
)
water_app = typer.Typer(help="Hydration tracking & fluid balance commands")
inventory_app = typer.Typer(help="Inventory stock, location management & shelf-life")
meals_app = typer.Typer(help="Culinary solver & recipe optimization")
ledger_app = typer.Typer(help="Cryptographic Nutrition & Cost Ledger inspection")

app.add_typer(water_app, name="water")
app.add_typer(inventory_app, name="inventory")
app.add_typer(meals_app, name="meals")
app.add_typer(ledger_app, name="ledger")

console = Console(force_terminal=True)


def get_db_session() -> Session:
    init_db()
    sess = Session(engine)
    cat_svc = CatalogService(sess)
    cat_svc.seed_defaults_if_empty()
    opt_svc = OptimizerService(sess)
    opt_svc.seed_recipes_if_empty()
    hyd_svc = HydrationService(sess)
    hyd_svc.ensure_default_user_and_water_preference()
    return sess


# ----------------------------------------------------
# HYDRATION COMMANDS
# ----------------------------------------------------
@water_app.command("log")
def water_log(
    amount_ml: float = typer.Argument(..., help="Fluid amount in milliliters"),
    source: str = typer.Option("Pure Spring Water", "--source", "-s", help="Fluid source"),
):
    """Quickly log water/hydration intake."""
    session = get_db_session()
    service = HydrationService(session)
    service.log_fluid(amount_ml=amount_ml, source_name=source)
    status = service.get_hydration_status()
    session.close()

    rprint(f"[bold cyan]💧 Logged +{amount_ml}ml[/bold cyan] from [white]{source}[/white]")
    rprint(
        f"[dim]Today's Hydration:[/] [bold green]{status.current_ml}ml[/] / "
        f"[white]{status.target_ml}ml[/] ([bold cyan]{status.percent_achieved}%[/])"
    )
    rprint(f'[italic cyan]"{status.preference_note}"[/italic cyan]')


@water_app.command("status")
def water_status():
    """Display current hydration pacing and food water breakdown."""
    session = get_db_session()
    service = HydrationService(session)
    status = service.get_hydration_status()
    session.close()

    panel_text = (
        f"[bold white]Daily Target:[/] {status.target_ml} ml\n"
        f"[bold cyan]Total Consumed:[/] {status.current_ml} ml ({status.percent_achieved}%)\n"
        f"  • Direct Pure Fluid: {status.direct_water_ml} ml\n"
        f"  • Inherent from Food: {status.food_water_ml} ml\n"
        f"[bold yellow]Remaining Today:[/] {status.remaining_ml} ml\n\n"
        f'[italic cyan]"{status.preference_note}"[/italic cyan]'
    )
    console.print(Panel(panel_text, title="💧 Hydration Balance Radar", border_style="cyan"))


# ----------------------------------------------------
# INVENTORY COMMANDS
# ----------------------------------------------------
@inventory_app.command("list")
def inventory_list(
    location: str | None = typer.Option(
        None,
        "--location",
        "-l",
        help="Filter by location (fridge, freezer, pantry, cabinet, counter)",
    ),
):
    """List physical stored food batches with color-coded shelf-life decay status."""
    session = get_db_session()
    service = InventoryService(session)

    target_loc = StorageLocation(location.lower()) if location else None
    items = service.list_inventory(location=target_loc)
    session.close()

    if not items:
        rprint("[yellow]Inventory is empty.[/yellow] Ingest groceries with `oopple ingest`.")
        return

    table = Table(title="📦 Oopple Stored Inventory Matrix", border_style="green")
    table.add_column("ID", style="dim")
    table.add_column("Item Name", style="bold white")
    table.add_column("Location", style="cyan")
    table.add_column("Quantity", justify="right")
    table.add_column("Shelf-Life Status", style="bold")
    table.add_column("Expires In", justify="right")

    for it in items:
        urgency_style = "green"
        urgency_text = f"Fresh ({it.days_remaining}d)"
        if it.urgency.value == "critical_today":
            urgency_style = "bold red"
            urgency_text = f"CRITICAL TODAY ({it.days_remaining}d)"
        elif it.urgency.value == "use_soon":
            urgency_style = "bold yellow"
            urgency_text = f"USE SOON ({it.days_remaining}d)"

        table.add_row(
            str(it.item.id),
            it.intake_unit.name,
            it.item.storage_location.value.capitalize(),
            f"{it.item.quantity} {it.item.unit.value}",
            f"[{urgency_style}]{urgency_text}[/{urgency_style}]",
            f"{it.days_remaining} days",
        )

    console.print(table)


# ----------------------------------------------------
# INGESTION COMMANDS
# ----------------------------------------------------
@app.command("scan")
def scan_barcode(
    barcode: str = typer.Argument(..., help="UPC or EAN barcode number"),
):
    """Scan / lookup a barcode via OpenFoodFacts and view nutrition facts."""
    session = get_db_session()
    service = CatalogService(session)

    unit = asyncio.run(service.lookup_or_fetch_barcode(barcode))
    session.close()

    if not unit:
        rprint(f"[red]Error:[/] Product with barcode '{barcode}' not found.")
        return

    panel = (
        f"[bold white]{unit.name}[/] ({unit.brand or 'Generic'})\n"
        f"[dim]SKU:[/] {unit.sku} | [dim]Cuisine:[/] {unit.cuisine_type.value}\n\n"
        f"[bold green]Serving:[/] {unit.serving_size} {unit.serving_unit.value}\n"
        f"🔥 [bold yellow]{unit.calories} kcal[/] | 🥩 [bold green]{unit.protein_g}g Protein[/] | "
        f"🍞 [bold blue]{unit.carbs_g}g Carbs[/] | 🥑 [bold magenta]{unit.fat_g}g Fat[/] | "
        f"💧 [bold cyan]{unit.water_ml}ml Water[/]"
    )
    console.print(Panel(panel, title="📷 Barcode Resolution Result", border_style="green"))


@app.command("ingest")
def ingest_text(
    text: str = typer.Argument(..., help="Natural language list e.g. '2 lbs chicken, 500ml milk'"),
    location: str = typer.Option("fridge", "--location", "-l", help="Storage location"),
):
    """Batch-ingest natural language items into inventory and ledger."""
    session = get_db_session()
    ingest_svc = IngestionService(session)
    parsed = ingest_svc.parse_natural_language_text(text)

    loc = StorageLocation(location.lower())
    ingested_count = 0

    for it in parsed:
        if it.matched_unit:
            ingest_svc.ingest_item(
                intake_unit_id=it.matched_unit.id,
                quantity=it.quantity,
                unit=it.unit,
                storage_location=loc,
                cost_basis=it.estimated_cost,
                source="cli_text_import",
            )
            rprint(
                f"  [green]✓ Ingested:[/] {it.quantity} {it.unit.value} "
                f"[bold white]{it.matched_unit.name}[/] -> [cyan]{loc.value}[/]"
            )
            ingested_count += 1
        else:
            rprint(f"  [yellow]⚠ Unmatched item:[/] {it.name}")

    session.close()
    rprint(f"[bold green]Successfully acquired {ingested_count} batches into storage![/]")


# ----------------------------------------------------
# OPTIMIZER & MEALS COMMANDS
# ----------------------------------------------------
@meals_app.command("suggest")
def meals_suggest(
    expiry_bias: float = typer.Option(
        3.5,
        "--expiry-bias",
        "-e",
        help="Urgency weight for near-expiring items",
    ),
):
    """Run multi-objective solver to recommend recipes from stored stock."""
    session = get_db_session()
    opt_svc = OptimizerService(session)
    recommendations = opt_svc.suggest_meals(weight_expiry=expiry_bias)
    session.close()

    if not recommendations:
        rprint("[yellow]No recipes available.[/yellow]")
        return

    table = Table(title="🍳 Oopple Multi-Objective Meal Recommendations", border_style="cyan")
    table.add_column("Recipe Name", style="bold white")
    table.add_column("Score", justify="right", style="bold yellow")
    table.add_column("Stock Match", justify="right")
    table.add_column("Expiry Priority Utilized", style="magenta")
    table.add_column("Calories / Macros", style="dim")

    for rec in recommendations[:5]:
        match_pct = f"{int(rec.inventory_match_ratio * 100)}%"
        match_style = "green" if rec.inventory_match_ratio >= 1.0 else "yellow"
        exp_text = (
            ", ".join(rec.expiring_ingredients_used) if rec.expiring_ingredients_used else "None"
        )

        table.add_row(
            rec.recipe.name,
            f"{rec.score:.1f}",
            f"[{match_style}]{match_pct}[/{match_style}]",
            exp_text,
            f"{int(rec.total_calories)} kcal | {int(rec.total_protein_g)}g P | "
            f"{int(rec.total_carbs_g)}g C",
        )

    console.print(table)


# ----------------------------------------------------
# LEDGER COMMANDS
# ----------------------------------------------------
@ledger_app.command("verify")
def ledger_verify():
    """Verify SHA-256 cryptographic hash chain integrity."""
    session = get_db_session()
    service = LedgerService(session)
    valid, msg = service.verify_ledger_integrity()
    summary = service.get_daily_summary()
    session.close()

    if valid:
        rprint(f"[bold green]🔒 Ledger Cryptographic Integrity Valid:[/] {msg}")
    else:
        rprint(f"[bold red]❌ Ledger Integrity Compromised:[/] {msg}")

    cals = summary["total_calories"]
    prot = summary["total_protein_g"]
    water = summary["total_water_ml"]
    spend = summary["spend_today"]
    waste = summary["waste_cost_today"]
    rprint(
        f"[dim]Today's Totals:[/] [yellow]{cals} kcal[/] • [green]{prot}g Prot[/] • "
        f"[cyan]{water}ml Water[/] • [white]Spend: ${spend:.2f}[/] • [red]Waste: ${waste:.2f}[/]"
    )


# ----------------------------------------------------
# SERVE WEB APP
# ----------------------------------------------------
@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
):
    """Start the Oopple FastAPI web server and interactive UI."""
    rprint(f"[bold green]Starting Oopple Engine at[/] [cyan]http://{host}:{port}[/]")
    rprint(f"[dim]API Swagger Documentation:[/] [cyan]http://{host}:{port}/docs[/]")
    uvicorn.run("oopple.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
