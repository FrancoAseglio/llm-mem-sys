// Small conveniences; every page also works without JavaScript.

// Open a form's URL with its filled-in fields only, so menus left on "all" stay out of the
// address. Nothing on the page is changed first, so the Back button finds the form as it was.
function openForm(form, only) {
  const params = new URLSearchParams();
  for (const [name, value] of new FormData(form)) {
    if (value && (!only || only.includes(name))) params.append(name, value);
  }
  const query = params.toString();
  window.location.assign(form.action + (query ? `?${query}` : ""));
}

// Results: the list reloads as soon as a menu changes (the mode boxes are handled below).
document.querySelectorAll("form[data-autosubmit]").forEach((form) => {
  form.addEventListener("change", (event) => {
    if (event.target.name !== "mode") openForm(form);
  });
});

// Results: the mode boxes show or hide each mode's column, chip and card straight away. The
// choice goes into the address (no `mode` at all when every mode is shown) and into the links
// to questions, the pager and the list, so it follows you around.
document.querySelectorAll("[data-mode-toggles]").forEach((toggles) => {
  if (toggles.closest("#ask-form")) return; // the inspector has its own handler
  const boxes = [...toggles.querySelectorAll('input[name="mode"]')];
  toggles.addEventListener("change", (event) => {
    let checked = boxes.filter((b) => b.checked).map((b) => b.value);
    if (!checked.length) {
      event.target.checked = true; // keep at least one mode
      checked = [event.target.value];
    }
    document.querySelectorAll("[data-mode]").forEach((el) => {
      el.hidden = !checked.includes(el.dataset.mode);
    });
    document.querySelectorAll("[data-cards]").forEach((grid) => {
      const visible = grid.querySelectorAll(".card:not([hidden])").length;
      grid.style.setProperty("--cards", Math.max(visible, 1));
    });
    const url = new URL(window.location);
    url.searchParams.delete("mode");
    if (checked.length < boxes.length) checked.forEach((m) => url.searchParams.append("mode", m));
    history.replaceState(null, "", url);
    // Links: a question or pager link carries the filters but not the run (it is in the
    // path); the link back to the list carries the run too.
    const run = window.location.pathname.split("/")[2];
    document.querySelectorAll("[data-base]").forEach((el) => {
      const params = new URLSearchParams(url.search);
      if (el.hasAttribute("data-keep-run")) {
        if (run && !params.has("run")) params.set("run", run);
      } else {
        params.delete("run");
      }
      const query = params.toString();
      const target = el.dataset.base + (query ? `?${query}` : "");
      if (el.tagName === "A") el.href = target;
      else el.dataset.href = target;
    });
  });
});

// Inspector: choosing a user opens their memory (the question and modes wait for Ask).
document.querySelectorAll("select[data-autosubmit-field]").forEach((select) => {
  select.addEventListener("change", () => openForm(select.form, [select.name]));
});

// Inspector: once a question is asked, the mode boxes show or hide its cards straight away.
// Ticking a mode that has no card yet asks again with the new choice.
const askForm = document.getElementById("ask-form");
const cards = document.getElementById("cards");
if (askForm && cards) {
  askForm.querySelectorAll('input[name="mode"]').forEach((box) => {
    box.addEventListener("change", () => {
      const checked = [...askForm.querySelectorAll('input[name="mode"]:checked')].map((b) => b.value);
      const shown = [...cards.querySelectorAll(".card")].map((c) => c.dataset.mode);
      if (checked.some((m) => !shown.includes(m))) {
        askForm.requestSubmit();
        return;
      }
      cards.querySelectorAll(".card").forEach((c) => (c.hidden = !checked.includes(c.dataset.mode)));
      cards.style.setProperty("--cards", Math.max(checked.length, 1));
      const url = new URL(window.location);
      url.searchParams.delete("mode");
      checked.forEach((m) => url.searchParams.append("mode", m));
      history.replaceState(null, "", url);
    });
  });
}

// A click anywhere on a question row opens it.
document.querySelectorAll("tr[data-href]").forEach((row) => {
  row.addEventListener("click", (event) => {
    if (!event.target.closest("a")) window.location = row.dataset.href;
  });
});

// Left and right arrow keys step through the list on a question page.
document.addEventListener("keydown", (event) => {
  if (event.target.closest("input, select, textarea")) return;
  const link = { ArrowLeft: "prev", ArrowRight: "next" }[event.key];
  const target = link && document.getElementById(link);
  if (target) window.location = target.href;
});

// The theme button switches light and dark and remembers the choice in this browser.
const toggle = document.getElementById("theme-toggle");
if (toggle) {
  const label = () => {
    toggle.textContent = document.documentElement.dataset.theme === "dark" ? "Light" : "Dark";
  };
  label();
  toggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    label();
  });
}

// Inspector: fetch each mode's answer in turn (the model answers one at a time anyway), with
// a running clock so a slow answer does not look stuck.
(async () => {
  for (const slot of document.querySelectorAll("[data-answer-url]")) {
    const waiting = slot.querySelector(".waiting");
    const start = Date.now();
    const clock = setInterval(() => {
      waiting.textContent = `Waiting for the model… ${Math.round((Date.now() - start) / 1000)} s`;
    }, 1000);
    try {
      const response = await fetch(slot.dataset.answerUrl);
      slot.innerHTML = await response.text();
    } catch (e) {
      slot.innerHTML = `<p class="notice">The dashboard did not respond: ${e}</p>`;
    } finally {
      clearInterval(clock);
    }
  }
})();
