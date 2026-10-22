// Wohinder swipe app: loads the feed from the API and lets you swipe through it.
// Plain JavaScript, no framework: everything happens in this one file.

"use strict";

const SWIPE_THRESHOLD = 110;   // px a card must be dragged to count as a swipe
const DRAG_START = 8;          // px of sideways movement before a touch becomes a drag
const PROFILE_KEY = "wohinder.profile";
const FILTER_KEY = "wohinder.filters.";   // + profile id

const TYPE_LABELS = {
  einzelzimmer: "Einzelzimmer",
  wg_2: "2er-WG",
  wg_3: "3er-WG",
  wg_4: "4er-WG+",
  wohnung_2_zimmer: "2-Zimmer-Wohnung",
};

const SOURCE_LABELS = {
  "wg-gesucht": "WG-Gesucht",
  kleinanzeigen: "Kleinanzeigen",
  immoscout: "ImmoScout24",
};

const $ = (id) => document.getElementById(id);

const state = {
  profiles: [],
  profileId: null,
  allCards: [],     // whole feed from the server, best first
  cards: [],        // allCards after filters: what the deck shows
  history: [],      // swipes of this session, for undo: {item, direction}
  saved: [],        // right swipes with their Anfrage
  filters: { types: [], minScore: 0 },
  busy: false,      // true while a card flies out, so double taps don't swipe twice
};

// --- Small helpers ---------------------------------------------------------

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${path}: ${response.status}`);
  return response.json();
}

// Escape text before putting it into HTML, so a listing can't inject markup.
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatDate(iso) {
  if (!iso) return "unbekannt";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

function formatKm(km) {
  if (km == null) return "?";
  return km.toFixed(1).replace(".", ",") + " km";   // German decimal comma
}

function level(share) {        // 0..1 → color class
  if (share >= 0.75) return "high";
  if (share >= 0.5) return "mid";
  return "low";
}

function shortName(profile) {
  // "Team (beide zusammen)" → "Team", so it fits the iPhone top bar
  return profile.display_name.split(" (")[0];
}

function storageGet(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 2200);
}

function showStatus(text) {
  $("status").textContent = text;
  $("status").hidden = !text;
}

// --- Cards -----------------------------------------------------------------

function cardElement({ listing, score }) {
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.id = listing.id;

  const bars = score.parts.map((part) => {
    const share = part.max ? part.points / part.max : 0;
    return `
      <div class="bar-row">
        <span>${esc(part.name)}</span>
        <div class="bar-track"><div class="bar-fill ${level(share)}" style="width:${Math.round(share * 100)}%"></div></div>
        <span class="bar-points">${part.points}/${part.max}</span>
      </div>`;
  }).join("");

  card.innerHTML = `
    <div class="card-header">
      <div class="card-source">${esc(SOURCE_LABELS[listing.source] || listing.source)}</div>
      <h2 class="card-title">${esc(listing.title)}</h2>
      <div class="score ${level(score.total / 100)}" aria-label="Score ${score.total} von 100">${score.total}</div>
    </div>
    <div class="card-body">
      <dl class="facts">
        <div class="fact"><dt>Warmmiete</dt><dd>${listing.warmmiete != null ? listing.warmmiete + " €" : "?"}</dd></div>
        <div class="fact"><dt>Größe</dt><dd>${listing.size_m2 != null ? String(listing.size_m2).replace(".", ",") + " m²" : "?"}</dd></div>
        <div class="fact"><dt>Typ</dt><dd>${esc(TYPE_LABELS[listing.housing_type] || "?")}</dd></div>
        <div class="fact"><dt>Frei ab</dt><dd>${formatDate(listing.available_from)}</dd></div>
        <div class="fact"><dt>Zur h_da</dt><dd>${formatKm(score.distance_km)}</dd></div>
        <div class="fact"><dt>Kontakt</dt><dd>${esc(listing.contact_name || "?")}</dd></div>
      </dl>
      ${listing.description ? `<p class="description">${esc(listing.description)}</p>` : ""}
      <h3 class="section-label">Warum ${score.total}?</h3>
      <div class="bars">${bars}</div>
      <ul class="reasons">${score.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
      <a class="listing-link" href="${esc(listing.url)}" target="_blank" rel="noopener">Anzeige öffnen ↗</a>
    </div>
    <div class="stamp stamp-yes">ANFRAGE</div>
    <div class="stamp stamp-no">WEITER</div>`;
  return card;
}

// Show the top two cards: the top one is swipeable, the second peeks out behind it.
function renderDeck() {
  const deck = $("deck");
  deck.querySelectorAll(".card").forEach((el) => el.remove());

  const visible = state.cards.slice(0, 2);
  // Insert in reverse so the top card ends up last in the DOM, i.e. on top.
  visible.slice().reverse().forEach((item, i) => {
    const el = cardElement(item);
    if (i === visible.length - 1) enableDrag(el);
    else el.classList.add("behind");
    deck.appendChild(el);
  });

  const empty = state.cards.length === 0;
  const filtered = state.allCards.length > 0;   // cards exist, but filters hide them
  $("empty").hidden = !empty;
  $("empty-title").textContent = filtered ? "Keine Matches mit diesen Filtern" : "Keine neuen Matches";
  $("empty-text").textContent = filtered
    ? `${state.allCards.length} Anzeigen sind ausgeblendet.`
    : "Du hast alle Anzeigen gesehen.";
  $("reset").textContent = filtered ? "Filter zurücksetzen" : "Alle wieder anzeigen";

  $("btn-left").disabled = empty;
  $("btn-right").disabled = empty;
  $("btn-undo").disabled = state.history.length === 0;
  $("feed-count").textContent = state.cards.length ? `(${state.cards.length})` : "";
}

// --- Dragging --------------------------------------------------------------
// Pointer events work for mouse and touch alike. The card has touch-action: pan-y,
// so vertical finger movement scrolls the card and only sideways movement drags it.

function enableDrag(card) {
  let startX = 0, startY = 0, dx = 0, pointerDown = false, dragging = false;
  const yes = card.querySelector(".stamp-yes");
  const no = card.querySelector(".stamp-no");

  card.addEventListener("pointerdown", (e) => {
    if (state.busy || e.button > 0) return;
    pointerDown = true;
    dragging = false;
    startX = e.clientX;
    startY = e.clientY;
    dx = 0;
  });

  card.addEventListener("pointermove", (e) => {
    if (!pointerDown) return;
    dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (!dragging) {
      // Only start dragging once the finger clearly moves sideways. Until then
      // taps still work (e.g. the "Anzeige öffnen" link) and scrolling stays native.
      if (Math.abs(dx) < DRAG_START || Math.abs(dx) < Math.abs(dy)) return;
      dragging = true;
      card.setPointerCapture(e.pointerId);  // keep events even if the finger leaves the card
      card.classList.remove("animate");
    }
    card.style.transform = `translate(${dx}px, ${dy * 0.3}px) rotate(${dx / 18}deg)`;
    yes.style.opacity = Math.max(0, Math.min(1, dx / SWIPE_THRESHOLD));
    no.style.opacity = Math.max(0, Math.min(1, -dx / SWIPE_THRESHOLD));
  });

  const end = () => {
    pointerDown = false;
    if (!dragging) return;
    dragging = false;
    if (dx > SWIPE_THRESHOLD) swipe("right");
    else if (dx < -SWIPE_THRESHOLD) swipe("left");
    else {
      // Not far enough: snap back to the middle
      card.classList.add("animate");
      card.style.transform = "";
      yes.style.opacity = 0;
      no.style.opacity = 0;
    }
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);   // iOS sends this when it starts scrolling
}

// --- Swiping & undo --------------------------------------------------------

async function swipe(direction) {
  if (state.busy || state.cards.length === 0) return;
  state.busy = true;

  const item = state.cards[0];
  const card = $("deck").querySelector(`.card[data-id="${item.listing.id}"]`);

  // Fly the card off screen
  if (card) {
    const x = (direction === "right" ? 1 : -1) * window.innerWidth * 1.5;
    card.classList.add("animate");
    card.style.transform = `translate(${x}px, 40px) rotate(${x / 30}deg)`;
    card.style.opacity = "0";
    card.querySelector(direction === "right" ? ".stamp-yes" : ".stamp-no").style.opacity = 1;
  }

  try {
    const result = await api("POST", `/profiles/${state.profileId}/swipes`,
                             { listing_id: item.listing.id, direction });
    state.allCards = state.allCards.filter((c) => c.listing.id !== item.listing.id);
    state.history.push({ item, direction });
    applyFilters();
    if (direction === "right") {
      state.saved.unshift({ ...item, anfrage: result.anfrage });  // ... = copy all fields
      renderSaved();
    }
    // Wait for the fly-out animation before drawing the next card
    setTimeout(() => {
      renderDeck();
      state.busy = false;
      if (result.anfrage) openAnfrage(result.anfrage, item.listing.url);
    }, 250);
  } catch (err) {
    console.error(err);
    toast("Keine Verbindung: Swipe nicht gespeichert");
    renderDeck();            // puts the card back
    state.busy = false;
  }
}

async function undo() {
  const last = state.history.at(-1);   // last element, like list.get(size - 1)
  if (!last || state.busy) return;
  try {
    await api("DELETE", `/profiles/${state.profileId}/swipes/${encodeURIComponent(last.item.listing.id)}`);
  } catch (err) {
    console.error(err);
    toast("Rückgängig hat nicht geklappt");
    return;
  }
  state.history.pop();
  state.allCards.unshift(last.item);    // back on top of the deck
  state.saved = state.saved.filter((s) => s.listing.id !== last.item.listing.id);
  applyFilters();
  // Show the card again even if a filter would hide it: you just swiped it
  if (!state.cards.includes(last.item)) state.cards.unshift(last.item);
  renderDeck();
  renderSaved();
  toast(last.direction === "right" ? "Anfrage verworfen" : "Zurückgeholt");
}

// --- Saved list ("Gemerkt") ------------------------------------------------

function renderSaved() {
  const list = $("saved-list");
  list.innerHTML = state.saved.map(({ listing, score }) => `
    <li class="saved-item" data-id="${esc(listing.id)}">
      <div class="saved-score ${level(score.total / 100)}">${score.total}</div>
      <div class="saved-text">
        <p class="saved-title">${esc(listing.title)}</p>
        <p class="saved-meta">${listing.warmmiete != null ? listing.warmmiete + " €" : "? €"} · ${esc(TYPE_LABELS[listing.housing_type] || "?")} · ab ${formatDate(listing.available_from)}</p>
      </div>
      <div class="saved-buttons">
        <button class="btn-secondary" data-action="show">Anfrage</button>
        <button class="btn-secondary" data-action="remove">Entfernen</button>
      </div>
    </li>`).join("");
  $("saved-empty").hidden = state.saved.length > 0;
  $("saved-count").textContent = state.saved.length ? `(${state.saved.length})` : "";
}

async function removeSaved(listingId) {
  const item = state.saved.find((s) => s.listing.id === listingId);
  if (!item) return;
  try {
    await api("DELETE", `/profiles/${state.profileId}/swipes/${encodeURIComponent(listingId)}`);
  } catch (err) {
    console.error(err);
    toast("Entfernen hat nicht geklappt");
    return;
  }
  state.saved = state.saved.filter((s) => s.listing.id !== listingId);
  state.history = state.history.filter((h) => h.item.listing.id !== listingId);
  // Back into the feed, at its place by score
  state.allCards.push({ listing: item.listing, score: item.score });
  state.allCards.sort((a, b) => b.score.total - a.score.total);
  applyFilters();
  renderSaved();
  renderDeck();
  toast("Wieder im Stapel");
}

// --- Tabs ------------------------------------------------------------------

function showTab(name) {
  const swipeTab = name === "swipe";
  $("view-swipe").hidden = !swipeTab;
  $("view-saved").hidden = swipeTab;
  $("tab-swipe").classList.toggle("active", swipeTab);
  $("tab-saved").classList.toggle("active", !swipeTab);
  $("tab-swipe").setAttribute("aria-selected", swipeTab);
  $("tab-saved").setAttribute("aria-selected", !swipeTab);
}

// --- Sheets ----------------------------------------------------------------

function openAnfrage(text, url) {
  $("anfrage").value = text;
  $("open-listing").href = url;
  $("sheet").hidden = false;
}

function closeSheets() {
  $("sheet").hidden = true;
  $("filter-sheet").hidden = true;
}

async function copyAnfrage() {
  try {
    await navigator.clipboard.writeText($("anfrage").value);
    toast("Kopiert");
  } catch {
    // No clipboard permission: select the text so it can be copied by hand
    $("anfrage").select();
    toast("Text markiert: jetzt kopieren");
  }
}

// --- Filters ---------------------------------------------------------------

function currentProfile() {
  return state.profiles.find((p) => p.id === state.profileId);
}

function applyFilters() {
  const { types, minScore } = state.filters;
  state.cards = state.allCards.filter(({ listing, score }) =>
    score.total >= minScore
    && (types.length === 0 || !listing.housing_type || types.includes(listing.housing_type)));
  const active = types.length > 0 || minScore > 0;
  $("filter-dot").hidden = !active;
}

function renderFilterSheet() {
  const profile = currentProfile();
  const { types, minScore } = state.filters;
  $("filter-types").innerHTML = profile.housing_types.map((t) => `
    <button class="chip-toggle" data-type="${esc(t)}"
            aria-pressed="${types.length === 0 || types.includes(t)}">${esc(TYPE_LABELS[t] || t)}</button>`).join("");
  $("min-score").value = minScore;
  $("min-score-value").textContent = minScore;
}

function readFilterSheet() {
  const all = [...document.querySelectorAll("#filter-types .chip-toggle")];
  const on = all.filter((b) => b.getAttribute("aria-pressed") === "true").map((b) => b.dataset.type);
  // All selected (or none) means "no type filter"
  state.filters.types = on.length === all.length ? [] : on;
  state.filters.minScore = Number($("min-score").value);
  storageSet(FILTER_KEY + state.profileId, state.filters);
  applyFilters();
  renderDeck();
}

function resetFilters() {
  state.filters = { types: [], minScore: 0 };
  storageSet(FILTER_KEY + state.profileId, state.filters);
  applyFilters();
  renderDeck();
}

// --- Loading ---------------------------------------------------------------

async function loadProfileData() {
  showStatus("Lade Matches …");
  $("empty").hidden = true;
  state.history = [];
  state.filters = storageGet(FILTER_KEY + state.profileId) || { types: [], minScore: 0 };
  try {
    // Promise.all: start both requests at once and wait for both
    const [feed, saved] = await Promise.all([
      api("GET", `/profiles/${state.profileId}/feed`),
      api("GET", `/profiles/${state.profileId}/saved`),
    ]);
    state.allCards = feed;
    state.saved = saved;
    showStatus("");
  } catch (err) {
    console.error(err);
    state.allCards = [];
    state.saved = [];
    showStatus("Server nicht erreichbar. Läuft uvicorn?");
  }
  applyFilters();
  renderDeck();
  renderSaved();
  if (!$("status").hidden) $("empty").hidden = true;
}

async function loadProfiles() {
  try {
    state.profiles = await api("GET", "/profiles");
  } catch (err) {
    console.error(err);
    showStatus("Server nicht erreichbar. Läuft uvicorn?");
    $("btn-left").disabled = $("btn-right").disabled = true;
    return;
  }
  $("profile").innerHTML = state.profiles
    .map((p) => `<option value="${esc(p.id)}">${esc(shortName(p))}</option>`)
    .join("");
  // Remember the last chosen profile on this phone
  const saved = storageGet(PROFILE_KEY);
  if (saved && state.profiles.some((p) => p.id === saved)) $("profile").value = saved;
  state.profileId = $("profile").value;
  await loadProfileData();
}

// --- Wiring ----------------------------------------------------------------

$("profile").addEventListener("change", (e) => {
  state.profileId = e.target.value;
  storageSet(PROFILE_KEY, state.profileId);
  loadProfileData();
});

$("btn-left").addEventListener("click", () => swipe("left"));
$("btn-right").addEventListener("click", () => swipe("right"));
$("btn-undo").addEventListener("click", undo);

$("reset").addEventListener("click", async () => {
  if (state.allCards.length > 0) return resetFilters();
  await api("DELETE", `/profiles/${state.profileId}/swipes`);
  loadProfileData();
});

$("tab-swipe").addEventListener("click", () => showTab("swipe"));
$("tab-saved").addEventListener("click", () => showTab("saved"));

// One listener for the whole list instead of one per button ("event delegation")
$("saved-list").addEventListener("click", (e) => {
  const button = e.target.closest("button");
  if (!button) return;
  const id = button.closest(".saved-item").dataset.id;
  if (button.dataset.action === "remove") removeSaved(id);
  if (button.dataset.action === "show") {
    const item = state.saved.find((s) => s.listing.id === id);
    if (item) openAnfrage(item.anfrage, item.listing.url);
  }
});

$("copy").addEventListener("click", copyAnfrage);
$("close-sheet").addEventListener("click", closeSheets);

$("btn-filter").addEventListener("click", () => {
  if (!currentProfile()) return;
  renderFilterSheet();
  $("filter-sheet").hidden = false;
});
$("filter-types").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip-toggle");
  if (!chip) return;
  chip.setAttribute("aria-pressed", chip.getAttribute("aria-pressed") !== "true");
  readFilterSheet();
});
$("min-score").addEventListener("input", (e) => {
  $("min-score-value").textContent = e.target.value;
  readFilterSheet();
});
$("filter-reset").addEventListener("click", () => {
  resetFilters();
  renderFilterSheet();
});
$("filter-done").addEventListener("click", closeSheets);

// Tap on the dark background closes a sheet
for (const id of ["sheet", "filter-sheet"]) {
  $(id).addEventListener("click", (e) => { if (e.target === $(id)) closeSheets(); });
}

// Keyboard on a laptop: ← skip, → Anfrage, Backspace undo, Esc closes sheets
document.addEventListener("keydown", (e) => {
  if (!$("sheet").hidden || !$("filter-sheet").hidden) {
    if (e.key === "Escape") closeSheets();
    return;
  }
  if ($("view-swipe").hidden) return;
  if (e.key === "ArrowLeft") swipe("left");
  if (e.key === "ArrowRight") swipe("right");
  if (e.key === "Backspace") undo();
});

// Register the service worker (offline start + "installable" PWA)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch((err) => console.warn("SW:", err));
}

loadProfiles();
