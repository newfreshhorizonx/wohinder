// Wohinder swipe app: loads the feed from the API and lets you swipe through it.
// Plain JavaScript, no framework: everything happens in this one file.

"use strict";

const SWIPE_THRESHOLD = 110;   // px a card must be dragged to count as a swipe
const PROFILE_KEY = "wohinder.profile";

const TYPE_LABELS = {
  einzelzimmer: "Einzelzimmer",
  wg_2: "2er-WG",
  wg_3: "3er-WG",
  wg_4: "4er-WG+",
  wohnung_2_zimmer: "2-Zimmer-Wohnung",
};

const $ = (id) => document.getElementById(id);

const state = {
  profileId: null,
  cards: [],        // feed items {listing, score}, best first
  busy: false,      // true while a card flies out, so double taps don't swipe twice
};

// --- API -------------------------------------------------------------------

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${path}: ${response.status}`);
  return response.json();
}

// --- Rendering -------------------------------------------------------------

// Escape text before putting it into HTML, so a listing title can't inject markup.
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

function scoreClass(total) {
  if (total >= 75) return "high";
  if (total >= 50) return "mid";
  return "low";
}

function cardElement({ listing, score }) {
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.id = listing.id;
  card.innerHTML = `
    <div class="card-header">
      <div class="card-source">${esc(listing.source)}</div>
      <h2 class="card-title">${esc(listing.title)}</h2>
      <div class="score ${scoreClass(score.total)}" aria-label="Score ${score.total} von 100">${score.total}</div>
    </div>
    <div class="card-body">
      <dl class="facts">
        <div class="fact"><dt>Warmmiete</dt><dd>${listing.warmmiete != null ? listing.warmmiete + " €" : "?"}</dd></div>
        <div class="fact"><dt>Größe</dt><dd>${listing.size_m2 != null ? listing.size_m2 + " m²" : "?"}</dd></div>
        <div class="fact"><dt>Typ</dt><dd>${esc(TYPE_LABELS[listing.housing_type] || "?")}</dd></div>
        <div class="fact"><dt>Frei ab</dt><dd>${formatDate(listing.available_from)}</dd></div>
      </dl>
      ${listing.description ? `<p class="description">${esc(listing.description)}</p>` : ""}
      <ul class="reasons">${score.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
    </div>
    <div class="stamp stamp-yes">ANFRAGE</div>
    <div class="stamp stamp-no">WEITER</div>`;
  return card;
}

// Show the top two cards: the top one is swipeable, the second peeks out behind it.
function render() {
  const deck = $("deck");
  deck.querySelectorAll(".card").forEach((el) => el.remove());

  const visible = state.cards.slice(0, 2);
  // Insert in reverse so the top card ends up last in the DOM, i.e. on top.
  visible.slice().reverse().forEach((item, i) => {
    const el = cardElement(item);
    const isTop = i === visible.length - 1;
    if (isTop) enableDrag(el);
    else el.classList.add("behind");
    deck.appendChild(el);
  });

  const empty = state.cards.length === 0;
  $("empty").hidden = !empty;
  $("btn-left").disabled = empty;
  $("btn-right").disabled = empty;
}

function showStatus(text) {
  $("status").textContent = text;
  $("status").hidden = !text;
}

function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 2200);
}

// --- Dragging --------------------------------------------------------------
// Pointer events work for mouse and touch alike.

function enableDrag(card) {
  let startX = 0, startY = 0, dx = 0, dy = 0, dragging = false;
  const yes = card.querySelector(".stamp-yes");
  const no = card.querySelector(".stamp-no");

  card.addEventListener("pointerdown", (e) => {
    if (state.busy) return;
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    card.setPointerCapture(e.pointerId);  // keep getting events even if the finger leaves the card
    card.classList.remove("animate");
  });

  card.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    dx = e.clientX - startX;
    dy = e.clientY - startY;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx / 18}deg)`;
    yes.style.opacity = Math.max(0, Math.min(1, dx / SWIPE_THRESHOLD));
    no.style.opacity = Math.max(0, Math.min(1, -dx / SWIPE_THRESHOLD));
  });

  const end = () => {
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
    dx = dy = 0;
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);
}

// --- Swiping ---------------------------------------------------------------

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
    state.cards.shift();
    // Wait for the fly-out animation before drawing the next card
    setTimeout(() => {
      render();
      state.busy = false;
      if (result.anfrage) openSheet(result.anfrage, item.listing.url);
    }, 250);
  } catch (err) {
    console.error(err);
    toast("Keine Verbindung: Swipe nicht gespeichert");
    render();            // puts the card back
    state.busy = false;
  }
}

// --- Anfrage sheet ---------------------------------------------------------

function openSheet(text, url) {
  $("anfrage").value = text;
  $("open-listing").href = url;
  $("sheet").hidden = false;
}

function closeSheet() {
  $("sheet").hidden = true;
}

async function copyAnfrage() {
  try {
    await navigator.clipboard.writeText($("anfrage").value);
    toast("Kopiert");
  } catch {
    // Older browsers / no permission: select the text so the user can copy by hand
    $("anfrage").select();
    toast("Text markiert: jetzt kopieren");
  }
}

// --- Loading ---------------------------------------------------------------

async function loadFeed() {
  showStatus("Lade Matches …");
  $("empty").hidden = true;
  try {
    state.cards = await api("GET", `/profiles/${state.profileId}/feed`);
    showStatus("");
    render();
  } catch (err) {
    console.error(err);
    state.cards = [];
    render();
    $("empty").hidden = true;
    showStatus("Server nicht erreichbar. Läuft uvicorn?");
  }
}

async function loadProfiles() {
  const select = $("profile");
  try {
    const profiles = await api("GET", "/profiles");
    select.innerHTML = profiles
      .map((p) => `<option value="${esc(p.id)}">${esc(p.display_name)}</option>`)
      .join("");
    // Remember the last chosen profile on this phone
    let saved = null;
    try { saved = localStorage.getItem(PROFILE_KEY); } catch {}
    if (saved && profiles.some((p) => p.id === saved)) select.value = saved;
    state.profileId = select.value;
    await loadFeed();
  } catch (err) {
    console.error(err);
    showStatus("Server nicht erreichbar. Läuft uvicorn?");
    $("btn-left").disabled = $("btn-right").disabled = true;
  }
}

// --- Wiring ----------------------------------------------------------------

$("profile").addEventListener("change", (e) => {
  state.profileId = e.target.value;
  try { localStorage.setItem(PROFILE_KEY, state.profileId); } catch {}
  loadFeed();
});

$("btn-left").addEventListener("click", () => swipe("left"));
$("btn-right").addEventListener("click", () => swipe("right"));

$("reset").addEventListener("click", async () => {
  await api("DELETE", `/profiles/${state.profileId}/swipes`);
  loadFeed();
});

$("copy").addEventListener("click", copyAnfrage);
$("close-sheet").addEventListener("click", closeSheet);
$("sheet").addEventListener("click", (e) => {
  if (e.target === $("sheet")) closeSheet();   // tap on the dark background closes it
});

// Arrow keys on a laptop: ← skip, → Anfrage, Esc closes the preview
document.addEventListener("keydown", (e) => {
  if (!$("sheet").hidden) {
    if (e.key === "Escape") closeSheet();
    return;
  }
  if (e.key === "ArrowLeft") swipe("left");
  if (e.key === "ArrowRight") swipe("right");
});

// Register the service worker (needed for offline start and "installable" PWA)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch((err) => console.warn("SW:", err));
}

loadProfiles();
