// The online harness page. Every value that comes from a student's service is written with
// textContent, never as HTML: a service under test must not be able to inject script here.
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const form = $("run-form");
  const urlInput = $("url");
  const keyInput = $("api-key");
  const runButton = $("run");
  const formError = $("form-error");
  const statusBox = $("status");
  const statusText = $("status-text");
  const bar = $("bar");
  const result = $("result");
  const POLL_MS = 2000;
  let report = null;

  const store = {
    get(key, fallback) {
      try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: no memory */ }
    },
  };

  function el(tag, className, ...children) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    for (const child of children) if (child !== null && child !== undefined) node.append(child);
    return node;
  }

  function link(label, href) {
    const a = el("a", "", label);
    a.href = href; // always a path from this site, never from the service under test
    return a;
  }

  function selectedWeek() {
    return Number(form.querySelector('input[name="week"]:checked').value);
  }

  function showError(message) {
    formError.textContent = message;
    formError.hidden = !message;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "same-origin", ...options });
    if (response.status === 401) {
      window.location.href = "/auth/login?next=/score/";
      throw new Error("Your session ended. Signing you in again.");
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `The site answered ${response.status}.`);
    return body;
  }

  function setRunning(running) {
    runButton.disabled = running;
    runButton.textContent = running ? "Running…" : "Run the harness";
  }

  function showProgress(run) {
    statusBox.hidden = false;
    const done = Math.min(run.completed, run.total);
    bar.style.width = `${Math.round((100 * done) / Math.max(run.total, 1))}%`;
    if (run.status === "queued") {
      statusText.textContent = run.position > 0
        ? `Queued: ${run.position} run${run.position === 1 ? "" : "s"} ahead of yours.`
        : "Starting…";
    } else {
      statusText.textContent = `Week ${run.week} against ${run.target}: check ${Math.min(done + 1, run.total)} of ${run.total}`
        + (run.current ? ` (${run.current})` : "") + ". The first call can take 20 s if your app scaled to zero.";
    }
  }

  async function poll(id) {
    setRunning(true);
    sessionStorage.setItem("activeRun", id);
    try {
      for (;;) {
        const run = await api(`/api/runs/${encodeURIComponent(id)}`);
        if (run.status === "done") { finish(run); return; }
        if (run.status === "failed") throw new Error(run.error || "The run failed.");
        showProgress(run);
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      }
    } catch (error) {
      statusBox.hidden = true;
      showError(error.message);
    } finally {
      sessionStorage.removeItem("activeRun");
      setRunning(false);
    }
  }

  function finish(run) {
    statusBox.hidden = true;
    report = run.report;
    render(run);
    const history = store.get("history", []);
    history.unshift({ week: run.week, score: report.score, target: run.target, at: report.started_at });
    store.set("history", history.slice(0, 10));
    renderHistory();
    result.hidden = false;
    $("result-title").focus({ preventScroll: true });
    result.scrollIntoView({ block: "start" });
  }

  function status(check) {
    if (check.passed) return "pass";
    return check.score > 0 ? "part" : "fail";
  }

  function render(run) {
    const checks = report.checks;
    const totalWeight = checks.reduce((sum, c) => sum + c.weight, 0) || 1;
    const lost = (c) => (100 * c.weight * (1 - c.score)) / totalWeight;
    const passed = checks.filter((c) => c.passed).length;
    const service = report.service || {};

    $("score").textContent = report.score.toFixed(1);
    $("score-caption").textContent = `Week ${run.week} · ${run.week_title} · ${run.target}`;
    $("score-count").textContent = `${passed} of ${checks.length} checks pass. Service version ${service.version ?? "?"}, `
      + `student ${service.student_id ?? "?"}, run in ${Math.round(report.duration_s)} s with harness ${report.harness_version}.`;

    const weekLinks = $("week-links");
    weekLinks.replaceChildren(...run.links.flatMap((l, i) => (i ? [" · ", link(l.label, l.href)] : [link(l.label, l.href)])));

    const next = $("next");
    const worst = checks.filter((c) => !c.passed).sort((a, b) => lost(b) - lost(a)).slice(0, 3);
    // w10.auth calls without the key on purpose; a 401 anywhere else means the key is missing or wrong.
    const unauthorized = checks.some((c) => c.id !== "w10.auth" && (c.exchanges || []).some((e) => e.status === 401));
    next.hidden = false;
    if (worst.length) {
      next.className = "callout";
      const warning = unauthorized
        ? [el("p", "key-warning", el("strong", "", "Your service answered 401 Unauthorized. "),
          "It requires the API key you turned on in Week 10: paste it in the API key field and run again.")]
        : [];
      next.replaceChildren(
        ...warning,
        el("p", "", el("strong", "", "Fix next: "), "the checks that cost you the most points."),
        el("ol", "", ...worst.map((c) => el("li", "", `${c.title}: ${lost(c).toFixed(1)} points`))),
      );
    } else {
      next.className = "callout callout--green";
      next.replaceChildren(el("p", "", el("strong", "", "Every check passes. "),
        "Score the earlier weeks on the same URL too: the service is cumulative."));
    }

    $("checks").replaceChildren(...checks.map((c) => renderCheck(c, run.advice[c.id] || {}, lost(c))));
  }

  function renderCheck(check, advice, pointsLost) {
    const kind = status(check);
    const head = el("div", "check-head",
      el("span", `chip chip--${kind}`, kind.toUpperCase()),
      el("span", "check-title", check.title, " ", el("code", "", check.id)),
      el("span", "check-score", `${Math.round(check.score * 100)}%`),
      el("span", "check-weight", pointsLost > 0.05 ? `−${pointsLost.toFixed(1)} pts` : `weight ${check.weight}`),
    );
    const item = el("li", `check check--${kind}`, head, el("p", "check-detail", check.detail));
    if (!check.passed && advice.hint) {
      const files = (advice.files || []).flatMap((f, i) => (i ? [", ", link(f.label, f.href)] : [link(f.label, f.href)]));
      item.append(el("p", "check-hint", el("strong", "", "What to try: "), advice.hint,
        files.length ? el("span", "files", " Open ", ...files, ".") : null));
    }
    if (check.exchanges && check.exchanges.length) item.append(renderEvidence(check.exchanges));
    return item;
  }

  function renderEvidence(exchanges) {
    const list = el("ol", "exchanges");
    for (const ex of exchanges.slice(0, 40)) {
      const outcome = ex.status ?? ex.error ?? "no answer";
      const row = el("li", "", el("code", "", `${ex.method} ${ex.path} → ${outcome} · ${(ex.latency_ms / 1000).toFixed(1)} s`));
      if (ex.request !== null && ex.request !== undefined) row.append(el("pre", "", "sent: " + pretty(ex.request)));
      if (ex.response !== null && ex.response !== undefined) row.append(el("pre", "", "got:  " + pretty(ex.response)));
      list.append(row);
    }
    const more = exchanges.length > 40 ? ` (first 40 of ${exchanges.length})` : "";
    return el("details", "evidence", el("summary", "", `Evidence: ${exchanges.length} call${exchanges.length === 1 ? "" : "s"}${more}`), list);
  }

  function pretty(value) {
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function renderHistory() {
    const history = store.get("history", []);
    $("history-section").hidden = history.length === 0;
    $("history").replaceChildren(...history.map((h) => el("li", "",
      el("b", "", `Week ${h.week}: ${Number(h.score).toFixed(1)}`),
      ` · ${new Date(h.at).toLocaleString()} · ${h.target}`)));
  }

  $("download").addEventListener("click", () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const a = link("", URL.createObjectURL(blob));
    a.download = `week${String(report.week).padStart(2, "0")}-${report.started_at.replace(/[:+]/g, "")}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const url = urlInput.value.trim();
    if (!url) { showError("Paste the URL of your deployed service."); urlInput.focus(); return; }
    const week = selectedWeek();
    store.set("url", url);
    store.set("week", week);
    result.hidden = true;
    setRunning(true);
    try {
      const run = await api("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, week, api_key: keyInput.value.trim() || null }),
      });
      showProgress(run);
      await poll(run.id);
    } catch (error) {
      showError(error.message);
      setRunning(false);
    }
  });

  async function start() {
    urlInput.value = store.get("url", "");
    const week = form.querySelector(`input[name="week"][value="${Number(store.get("week", 5))}"]`);
    if (week) week.checked = true;
    renderHistory();
    try {
      await api("/api/me"); // an expired session goes to sign-in now, not after the form is filled
    } catch { /* the page still works; api() redirects to sign-in on 401 */ }
    const active = sessionStorage.getItem("activeRun");
    if (active) poll(active);
  }

  start();
})();
