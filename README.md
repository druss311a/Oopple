# Oopple 🍏💧

> **Intelligent Nutrition, Inventory Lifecycle & Culinary Optimization Engine**

Oopple reimagines nutrition and food management as an interconnected, event-sourced continuum. Every food, ingredient, and hydration item is an **Intake Unit** that flows from acquisition (or garden harvest) to storage (fridge/freezer/pantry/cabinet), culinary preparation, consumption, and financial/nutritional depreciation.

---

## ✨ Key Features

- 🔄 **Intake Unit Lifecycle Pipeline**: Full provenance tracking from pre-purchase/harvest $\rightarrow$ storage $\rightarrow$ prep $\rightarrow$ consumption/depreciation.
- ⛓️ **Nutrition & Cost Ledger**: Event-sourced immutable audit trail for tracking macros, micronutrients, hydration balance, and food expenditure efficiency.
- ⚡ **Multi-Objective Culinary Optimizer**: Intelligently recommends recipes balancing ingredient shelf-life/expiry urgency, nutritional targets, budget, and taste preferences.
- 💧 **Foundational Hydration Tracking**: Built-in hydration tracking with the whimsical default premise (*"Trust us, your body likes water"*).
- 🔍 **Rapid Ingestion Modalities**: Barcode scanning integration (OpenFoodFacts API / USDA FoodData Central), AI text/receipt parsing, and quick capture.
- 💻 **Multiple Interfaces**: Modern responsive Web UI, interactive REST API with OpenAPI/Swagger docs, and a fast CLI.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) (recommended)

### Installation
```bash
# Clone the repository
git clone https://github.com/druss311a/Oopple.git
cd Oopple

# Install dependencies and sync virtual environment
uv sync --all-extras
```

### Running the API & Web Dashboard
```bash
uv run uvicorn oopple.api.app:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) to view the Web UI or [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger API documentation.

### Running Tests & Linting
```bash
uv run pytest -v
uv run ruff check .
```

---

## 🏗️ Architecture & Sprints

- **Sprint 0**: Infrastructure, Tooling (`uv` / Python 3.12), Scaffold & CI Workflows
- **Sprint 1**: Core Domain Models, Catalog Taxonomy, & Immutable Event Ledger
- **Sprint 2**: Fast Ingestion Pipelines (Barcode OpenFoodFacts/USDA API, AI Item Parser)
- **Sprint 3**: Dynamic Storage Decay & Multi-Objective Recipe Optimizer
- **Sprint 4**: FastAPI REST API & Hydration Tracking Engine
- **Sprint 5**: Premium Modern Responsive Web Application (Dark mode, visual matrix, live dials)
- **Sprint 6**: Typer CLI, End-to-End Verification & Release
