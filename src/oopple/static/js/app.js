/**
 * Oopple Web Application - Interactive Client Logic
 */

const API_BASE = "";

// Global State
let state = {
  activeTab: "dashboard",
  hydration: null,
  summary: null,
  inventory: [],
  recipes: [],
  recommendations: [],
  ledgerEntries: [],
  activeLocationFilter: "all",
  activeItemForAction: null,
};

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupEventListeners();
  loadAllData();
});

// Toast notification helper
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Navigation Tabs
function setupNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const targetId = tab.getAttribute("data-tab");
      document.querySelectorAll(".view-panel").forEach((panel) => {
        panel.classList.remove("active");
      });
      const targetPanel = document.getElementById(`view-${targetId}`);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
      state.activeTab = targetId;

      if (targetId === "inventory") loadInventory();
      if (targetId === "solver") loadRecommendations();
      if (targetId === "ledger") loadLedger();
    });
  });
}

// Event Listeners
function setupEventListeners() {
  // Quick Water buttons
  document.querySelectorAll(".btn-water-quick").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const amount = parseFloat(btn.getAttribute("data-amount"));
      await logWater(amount);
    });
  });

  // Location filter pills
  document.querySelectorAll(".filter-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeLocationFilter = pill.getAttribute("data-location");
      renderInventory();
    });
  });

  // Barcode Lookup Form
  const barcodeForm = document.getElementById("barcode-form");
  if (barcodeForm) {
    barcodeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const code = document.getElementById("barcode-input").value.trim();
      if (!code) return;
      await lookupBarcode(code);
    });
  }

  // NLP Parse Form
  const nlpForm = document.getElementById("nlp-form");
  if (nlpForm) {
    nlpForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = document.getElementById("nlp-text-input").value.trim();
      if (!text) return;
      await parseAndIngestText(text);
    });
  }

  // Modal Close buttons
  document.querySelectorAll(".btn-close-modal").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-overlay").forEach((m) => m.classList.remove("active"));
    });
  });

  // Consume submit
  const consumeForm = document.getElementById("consume-form");
  if (consumeForm) {
    consumeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const qty = parseFloat(document.getElementById("consume-qty-input").value);
      if (!state.activeItemForAction || qty <= 0) return;
      await submitConsume(state.activeItemForAction.id, qty);
    });
  }

  // Move location submit
  const moveForm = document.getElementById("move-form");
  if (moveForm) {
    moveForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const targetLoc = document.getElementById("move-location-select").value;
      if (!state.activeItemForAction) return;
      await submitMove(state.activeItemForAction.id, targetLoc);
    });
  }

  // Solver weight sliders
  const sliderExpiry = document.getElementById("slider-weight-expiry");
  if (sliderExpiry) {
    sliderExpiry.addEventListener("input", () => loadRecommendations());
  }
}

// Master Data Load
async function loadAllData() {
  await Promise.all([
    loadHydration(),
    loadDailySummary(),
    loadInventory(),
    loadRecommendations(),
    loadLedger(),
  ]);
}

// Hydration
async function loadHydration() {
  try {
    const res = await fetch(`${API_BASE}/api/hydration/status`);
    if (!res.ok) return;
    const data = await res.json();
    state.hydration = data;
    renderHydration();
  } catch (err) {
    console.error("Failed loading hydration", err);
  }
}

function renderHydration() {
  if (!state.hydration) return;
  const h = state.hydration;

  const valEl = document.getElementById("dial-current-val");
  const targetEl = document.getElementById("dial-target-val");
  const quoteEl = document.getElementById("hydration-quote-text");
  const circleEl = document.getElementById("dial-progress-circle");
  const directEl = document.getElementById("hydration-direct-text");
  const foodEl = document.getElementById("hydration-food-text");

  if (valEl) valEl.innerText = Math.round(h.current_ml);
  if (targetEl) targetEl.innerText = `Target: ${Math.round(h.target_ml)} ml`;
  if (quoteEl) quoteEl.innerText = `"${h.preference_note}"`;
  if (directEl) directEl.innerText = `${Math.round(h.direct_water_ml)} ml`;
  if (foodEl) foodEl.innerText = `${Math.round(h.food_water_ml)} ml`;

  if (circleEl) {
    const circumference = 440;
    const pct = Math.min(1.0, h.current_ml / h.target_ml);
    const offset = circumference - pct * circumference;
    circleEl.style.strokeDashoffset = offset;
  }
}

async function logWater(amountMl) {
  try {
    const res = await fetch(`${API_BASE}/api/hydration/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_ml: amountMl, source_name: "Quick Hydration Tap" }),
    });
    if (res.ok) {
      showToast(`Logged +${amountMl}ml Hydration! 💧`);
      await Promise.all([loadHydration(), loadDailySummary(), loadLedger()]);
    }
  } catch (err) {
    showToast("Failed to log hydration", "error");
  }
}

// Daily Summary & Macros
async function loadDailySummary() {
  try {
    const res = await fetch(`${API_BASE}/api/ledger/summary`);
    if (!res.ok) return;
    const data = await res.json();
    state.summary = data;
    renderDailySummary();
  } catch (err) {
    console.error("Failed to load summary", err);
  }
}

function renderDailySummary() {
  if (!state.summary) return;
  const s = state.summary;

  const calEl = document.getElementById("val-cal");
  const protEl = document.getElementById("val-prot");
  const carbsEl = document.getElementById("val-carbs");
  const fatEl = document.getElementById("val-fat");

  const fillCal = document.getElementById("fill-cal");
  const fillProt = document.getElementById("fill-prot");
  const fillCarbs = document.getElementById("fill-carbs");
  const fillFat = document.getElementById("fill-fat");

  const spendEl = document.getElementById("val-spend-today");
  const wasteEl = document.getElementById("val-waste-today");

  if (calEl) calEl.innerText = `${s.total_calories} / 2000 kcal`;
  if (protEl) protEl.innerText = `${s.total_protein_g} / 140 g`;
  if (carbsEl) carbsEl.innerText = `${s.total_carbs_g} / 200 g`;
  if (fatEl) fatEl.innerText = `${s.total_fat_g} / 65 g`;

  if (fillCal) fillCal.style.width = `${Math.min(100, (s.total_calories / 2000) * 100)}%`;
  if (fillProt) fillProt.style.width = `${Math.min(100, (s.total_protein_g / 140) * 100)}%`;
  if (fillCarbs) fillCarbs.style.width = `${Math.min(100, (s.total_carbs_g / 200) * 100)}%`;
  if (fillFat) fillFat.style.width = `${Math.min(100, (s.total_fat_g / 65) * 100)}%`;

  if (spendEl) spendEl.innerText = `$${s.spend_today.toFixed(2)}`;
  if (wasteEl) wasteEl.innerText = `$${s.waste_cost_today.toFixed(2)}`;
}

// Inventory
async function loadInventory() {
  try {
    const res = await fetch(`${API_BASE}/api/inventory`);
    if (!res.ok) return;
    const data = await res.json();
    state.inventory = data;
    renderInventory();
    renderExpiryStats();
  } catch (err) {
    console.error("Failed to load inventory", err);
  }
}

function renderExpiryStats() {
  const criticalCount = state.inventory.filter((i) => i.urgency === "critical_today").length;
  const warningCount = state.inventory.filter((i) => i.urgency === "use_soon").length;
  const freshCount = state.inventory.filter((i) => i.urgency === "fresh").length;
  const totalCount = state.inventory.length;

  const critEl = document.getElementById("stat-critical-count");
  const warnEl = document.getElementById("stat-warning-count");
  const freshEl = document.getElementById("stat-fresh-count");
  const totalEl = document.getElementById("stat-total-count");

  if (critEl) critEl.innerText = criticalCount;
  if (warnEl) warnEl.innerText = warningCount;
  if (freshEl) freshEl.innerText = freshCount;
  if (totalEl) totalEl.innerText = totalCount;
}

function renderInventory() {
  const container = document.getElementById("inventory-grid");
  if (!container) return;

  const filter = state.activeLocationFilter;
  const items =
    filter === "all" ? state.inventory : state.inventory.filter((i) => i.storage_location === filter);

  if (items.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">
        <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">No items stored in ${filter}.</p>
        <p style="font-size: 0.85rem;">Use the Quick Ingestion tab to add groceries or garden harvests!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = items
    .map((item) => {
      let urgencyBadgeClass = "badge-fresh";
      let urgencyLabel = `Fresh (${item.days_remaining}d)`;
      if (item.urgency === "critical_today") {
        urgencyBadgeClass = "badge-critical";
        urgencyLabel = `⚡ Expiring Today (${Math.max(0, item.days_remaining)}d)`;
      } else if (item.urgency === "use_soon") {
        urgencyBadgeClass = "badge-warning";
        urgencyLabel = `Use Soon (${item.days_remaining}d)`;
      }

      return `
      <div class="item-card ${item.urgency}">
        <div class="item-card-top">
          <div>
            <div class="item-name">${item.name}</div>
            <div class="item-meta">${item.brand || "Fresh"} • ${item.category}</div>
          </div>
          <div class="item-qty-badge">${item.quantity} ${item.unit}</div>
        </div>
        <div class="item-card-mid">
          <span class="shelf-life-badge ${urgencyBadgeClass}">${urgencyLabel}</span>
          <span style="color: var(--text-dim); font-size: 0.8rem;">📍 ${item.storage_location}</span>
        </div>
        <div class="item-card-actions">
          <button class="btn-card-action" onclick="openConsumeModal(${item.id})">🍽️ Eat</button>
          <button class="btn-card-action" onclick="openMoveModal(${item.id})">📦 Move</button>
          <button class="btn-card-action" style="color: #fb7185;" onclick="discardWaste(${item.id})">🗑️ Discard</button>
        </div>
      </div>
    `;
    })
    .join("");
}

// Inventory Modals & Actions
window.openConsumeModal = (itemId) => {
  const item = state.inventory.find((i) => i.id === itemId);
  if (!item) return;
  state.activeItemForAction = item;

  document.getElementById("consume-item-name").innerText = `${item.name} (${item.quantity} ${item.unit} on hand)`;
  const qtyInput = document.getElementById("consume-qty-input");
  qtyInput.value = item.quantity;
  qtyInput.max = item.quantity;

  document.getElementById("modal-consume").classList.add("active");
};

window.openMoveModal = (itemId) => {
  const item = state.inventory.find((i) => i.id === itemId);
  if (!item) return;
  state.activeItemForAction = item;

  document.getElementById("move-item-name").innerText = `${item.name} (Currently in ${item.storage_location})`;
  document.getElementById("modal-move").classList.add("active");
};

async function submitConsume(itemId, quantity) {
  try {
    const res = await fetch(`${API_BASE}/api/inventory/${itemId}/consume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    });
    if (res.ok) {
      showToast("Consumed item & logged to Nutrition Ledger! 🥗");
      document.getElementById("modal-consume").classList.remove("active");
      await loadAllData();
    }
  } catch (err) {
    showToast("Failed to consume item", "error");
  }
}

async function submitMove(itemId, targetLocation) {
  try {
    const res = await fetch(`${API_BASE}/api/inventory/${itemId}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_location: targetLocation }),
    });
    if (res.ok) {
      showToast(`Moved to ${targetLocation}! Shelf life updated. 📦`);
      document.getElementById("modal-move").classList.remove("active");
      await loadInventory();
    }
  } catch (err) {
    showToast("Failed to transfer item location", "error");
  }
}

window.discardWaste = async (itemId) => {
  if (!confirm("Are you sure you want to discard this item? Food waste will be recorded in the ledger.")) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/inventory/${itemId}/waste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "Expired / spoiled in storage" }),
    });
    if (res.ok) {
      showToast("Discarded item. Waste cost logged. 🗑️", "warning");
      await loadAllData();
    }
  } catch (err) {
    showToast("Failed to discard item", "error");
  }
};

// Optimizer & Culinary Solver
async function loadRecommendations() {
  try {
    const weightExpiry = document.getElementById("slider-weight-expiry")?.value || 3.5;
    const res = await fetch(`${API_BASE}/api/optimizer/suggest?weight_expiry=${weightExpiry}`);
    if (!res.ok) return;
    const data = await res.json();
    state.recommendations = data;
    renderRecommendations();
  } catch (err) {
    console.error("Failed to load recommendations", err);
  }
}

function renderRecommendations() {
  const container = document.getElementById("recipes-grid");
  if (!container) return;

  if (state.recommendations.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted);">No recommendations available.</p>`;
    return;
  }

  container.innerHTML = state.recommendations
    .map((rec) => {
      const matchPct = Math.round(rec.inventory_match_ratio * 100);
      const expiringHtml =
        rec.expiring_ingredients_used.length > 0
          ? `<div class="expiring-alert-pill">🔥 Uses near-expiry: ${rec.expiring_ingredients_used.join(", ")}</div>`
          : "";

      const missingHtml =
        rec.missing_ingredients.length > 0
          ? `<div style="font-size: 0.8rem; color: #fb7185; margin-top: 0.25rem;">Missing: ${rec.missing_ingredients.map((m) => `${m.name} (${m.required} ${m.unit})`).join(", ")}</div>`
          : `<div style="font-size: 0.8rem; color: #34d399; margin-top: 0.25rem;">✨ 100% In Stock in Pantry/Fridge!</div>`;

      return `
      <div class="recipe-card">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
              <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff;">${rec.recipe_name}</h3>
              <span style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase;">${rec.cuisine_type} • ⏱️ ${rec.prep_time_minutes + rec.cook_time_minutes}m</span>
            </div>
            <span class="recipe-score-tag">⚡ ${rec.score} pts</span>
          </div>

          ${expiringHtml}
          ${missingHtml}

          <div style="display: flex; gap: 0.75rem; font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; background: rgba(0,0,0,0.2); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm);">
            <span>🔥 <strong>${rec.total_calories}</strong> kcal</span>
            <span>🥩 <strong>${rec.total_protein_g}g</strong> prot</span>
            <span>🍞 <strong>${rec.total_carbs_g}g</strong> carbs</span>
            <span>🥑 <strong>${rec.total_fat_g}g</strong> fat</span>
          </div>
        </div>

        <button class="btn-primary" style="width: 100%;" onclick="cookMeal(${rec.recipe_id})">
          🍳 Cook & Log Meal
        </button>
      </div>
    `;
    })
    .join("");
}

window.cookMeal = async (recipeId) => {
  try {
    const res = await fetch(`${API_BASE}/api/optimizer/cook`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipe_id: recipeId, portions: 1.0 }),
    });
    if (res.ok) {
      showToast("Meal prepared! Ingredients deducted & nutrition logged to ledger. 🍳");
      await loadAllData();
    }
  } catch (err) {
    showToast("Failed to cook meal", "error");
  }
};

// Barcode & NLP Ingestion
async function lookupBarcode(barcode) {
  try {
    const previewEl = document.getElementById("barcode-result-preview");
    previewEl.innerHTML = `<p style="color: var(--cyan);">Scanning barcode & querying OpenFoodFacts...</p>`;

    const res = await fetch(`${API_BASE}/api/catalog/barcode/${barcode}`, { method: "POST" });
    if (!res.ok) {
      previewEl.innerHTML = `<p style="color: #fb7185;">Product not found for barcode ${barcode}.</p>`;
      return;
    }
    const unit = await res.json();
    previewEl.innerHTML = `
      <div style="background: var(--bg-surface-raised); padding: 1.25rem; border-radius: var(--radius-md); margin-top: 1rem; border: 1px solid var(--border-subtle);">
        <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 0.25rem;">${unit.name}</h4>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">${unit.brand || ""} • SKU: ${unit.sku}</p>
        <div style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 1rem;">
          🔥 ${unit.calories} kcal • 🥩 ${unit.protein_g}g Protein • 💧 ${unit.water_ml}ml Water
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn-primary" onclick="ingestFoundBarcode(${unit.id})">📥 Add 1 Unit to Fridge</button>
        </div>
      </div>
    `;
  } catch (err) {
    showToast("Barcode lookup failed", "error");
  }
}

window.ingestFoundBarcode = async (unitId) => {
  try {
    const res = await fetch(`${API_BASE}/api/inventory/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intake_unit_id: unitId,
        quantity: 1.0,
        unit: "piece",
        storage_location: "fridge",
        source: "barcode_scan",
      }),
    });
    if (res.ok) {
      showToast("Acquired item into fridge & recorded to ledger! 🍏");
      document.getElementById("barcode-result-preview").innerHTML = "";
      document.getElementById("barcode-input").value = "";
      await loadAllData();
    }
  } catch (err) {
    showToast("Failed to ingest item", "error");
  }
};

async function parseAndIngestText(text) {
  try {
    const previewEl = document.getElementById("nlp-result-preview");
    previewEl.innerHTML = `<p style="color: var(--cyan);">Parsing item strings...</p>`;

    const res = await fetch(`${API_BASE}/api/inventory/parse-text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return;
    const items = await res.json();

    if (items.length === 0) {
      previewEl.innerHTML = `<p style="color: #fb7185;">Could not parse items.</p>`;
      return;
    }

    previewEl.innerHTML = `
      <div style="background: var(--bg-surface-raised); padding: 1.25rem; border-radius: var(--radius-md); margin-top: 1rem; border: 1px solid var(--border-subtle);">
        <h4 style="font-size: 1rem; color: #fff; margin-bottom: 0.5rem;">Parsed ${items.length} items:</h4>
        <ul style="list-style: none; padding: 0; margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.35rem;">
          ${items.map((it) => `<li>• <strong>${it.quantity} ${it.unit}</strong> ${it.matched_unit_name || it.parsed_name}</li>`).join("")}
        </ul>
        <button class="btn-primary" onclick="batchImportParsed()">📥 Confirm & Ingest All to Inventory</button>
      </div>
    `;
    window.lastParsedItems = items;
  } catch (err) {
    showToast("Failed to parse text", "error");
  }
}

window.batchImportParsed = async () => {
  if (!window.lastParsedItems) return;
  for (const it of window.lastParsedItems) {
    if (it.matched_unit_id) {
      await fetch(`${API_BASE}/api/inventory/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          intake_unit_id: it.matched_unit_id,
          quantity: it.quantity,
          unit: it.unit,
          storage_location: "fridge",
          source: "nlp_text_import",
        }),
      });
    }
  }
  showToast("All items ingested to inventory & logged! 🍏");
  document.getElementById("nlp-result-preview").innerHTML = "";
  document.getElementById("nlp-text-input").value = "";
  await loadAllData();
};

// Ledger Explorer
async function loadLedger() {
  try {
    const [entriesRes, verifyRes] = await Promise.all([
      fetch(`${API_BASE}/api/ledger/entries?limit=25`),
      fetch(`${API_BASE}/api/ledger/verify`),
    ]);

    if (entriesRes.ok) {
      state.ledgerEntries = await entriesRes.json();
      renderLedger();
    }
    if (verifyRes.ok) {
      const verifyData = await verifyRes.json();
      const statusBadge = document.getElementById("ledger-verify-badge");
      if (statusBadge) {
        statusBadge.innerHTML = verifyData.is_valid
          ? `🔒 Hash Chain Verified (${verifyData.message})`
          : `⚠️ Integrity Mismatch: ${verifyData.message}`;
      }
    }
  } catch (err) {
    console.error("Failed to load ledger", err);
  }
}

function renderLedger() {
  const tbody = document.getElementById("ledger-tbody");
  if (!tbody) return;

  if (state.ledgerEntries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No ledger events logged yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = state.ledgerEntries
    .map((e) => {
      let eventColor = "#34d399";
      if (e.event_type === "waste_discard") eventColor = "#fb7185";
      if (e.event_type === "hydrate") eventColor = "#38bdf8";
      if (e.event_type === "consume") eventColor = "#fcd34d";

      const timeStr = new Date(e.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      return `
      <tr>
        <td><strong>#${e.sequence_number}</strong></td>
        <td><span style="color: ${eventColor}; font-weight: 700; text-transform: uppercase;">${e.event_type}</span></td>
        <td><strong>${e.intake_unit_name}</strong> (${e.quantity} ${e.unit})</td>
        <td>${Math.round(e.delta_calories)} kcal • ${Math.round(e.delta_protein_g)}g prot</td>
        <td>${Math.round(e.delta_water_ml)} ml</td>
        <td><span class="hash-badge">${e.current_hash.slice(0, 10)}...</span></td>
        <td style="color: var(--text-dim);">${timeStr}</td>
      </tr>
    `;
    })
    .join("");
}
