/* Course slide decks: navigation, scaling, contents panel and code highlighting.
   Keys: Right / Space / PageDown next, Left / PageUp previous, Home / End, C contents, F full screen, P print. */
(() => {
  const W = 1280;
  const H = 720;
  const stage = document.querySelector(".stage");
  if (!stage) return;
  const slides = [...stage.querySelectorAll(":scope > .slide")];
  if (!slides.length) return;
  const week = stage.dataset.week || "";
  const topic = stage.dataset.topic || "";
  const courseRoot = new URL("../", document.currentScript.src);
  const weekFolder = decodeURIComponent(location.pathname).match(/\/(week\d{2}-[^/]+)\//)?.[1];
  const titleOf = (s) => s.dataset.title || (s.querySelector("h1, h2")?.textContent || "").trim();

  // Chrome: brand and week on top, title, counter and controls at the bottom.
  stage.insertAdjacentHTML(
    "afterbegin",
    `<header class="chrome-top">
       <div class="brand"><b>Agentic AI on Microsoft Foundry</b><span>Pablo Salvador Lopez · github.com/pablosalvador10</span></div>
       <div class="week"><b>${week}</b> · ${topic}</div>
     </header>`
  );
  stage.insertAdjacentHTML(
    "beforeend",
    `<div class="progress" aria-hidden="true"></div>
     <footer class="chrome-bottom">
       <button class="nav-btn" data-act="toc" type="button" aria-expanded="false" aria-controls="toc" title="Contents (C)">Contents</button>
       <span class="slide-title"></span>
       <span class="counter" aria-hidden="true"></span>
       <button class="nav-btn" data-act="prev" type="button" aria-label="Previous slide" title="Previous (Left)">&larr;</button>
       <button class="nav-btn" data-act="next" type="button" aria-label="Next slide" title="Next (Right)">&rarr;</button>
     </footer>
    <nav class="toc" id="toc" aria-label="Slides" aria-hidden="true" inert><h4>${week} · Slides</h4><ol></ol></nav>
     <div class="sr-live" aria-live="polite" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></div>`
  );

  const progress = stage.querySelector(".progress");
  const titleEl = stage.querySelector(".slide-title");
  const counter = stage.querySelector(".counter");
  const prevBtn = stage.querySelector('[data-act="prev"]');
  const nextBtn = stage.querySelector('[data-act="next"]');
  const tocBtn = stage.querySelector('[data-act="toc"]');
  const toc = stage.querySelector(".toc");
  const live = stage.querySelector(".sr-live");
  const brand = stage.querySelector(".brand");
  const home = document.createElement("a");
  home.href = new URL("index.html", courseRoot).href;
  home.setAttribute("aria-label", "Course home · Agentic AI on Microsoft Foundry");
  home.append(...brand.childNodes);
  brand.append(home);
  const homeButton = document.createElement("a");
  homeButton.href = home.href;
  homeButton.className = "nav-btn deck-home-link";
  homeButton.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3.5 10.5 12 3.5l8.5 7"/><path d="M5.5 9v11h4.5v-6h4v6h4.5V9"/></svg>';
  homeButton.append("Course home");
  stage.querySelector(".chrome-top").append(homeButton);
  let lectureLink = null;
  if (weekFolder) {
    lectureLink = document.createElement("a");
    lectureLink.href = new URL(`${weekFolder}/docs/lecture.html`, courseRoot).href;
    lectureLink.className = "nav-btn deck-material-link";
    lectureLink.textContent = "Lecture";
    lectureLink.setAttribute("aria-label", "Read this week's lecture");
    tocBtn.after(lectureLink);
  }
  // Each slide names the lecture section it teaches (data-lecture="6"); the button follows it.
  function pointLectureAt(slide) {
    if (!lectureLink) return;
    const section = (slide.dataset.lecture || "").split(" ")[0];
    const numbered = /^\d+$/.test(section);
    const url = new URL(lectureLink.href);
    url.hash = numbered ? `s${section}` : "";
    lectureLink.href = url.href;
    lectureLink.textContent = numbered ? `Lecture §${section}` : "Lecture";
    lectureLink.setAttribute("aria-label", numbered ? `Read section ${section} of the lecture` : "Read this week's lecture");
  }

  const list = toc.querySelector("ol");
  slides.forEach((s, k) => {
    s.setAttribute("role", "group");
    s.setAttribute("aria-roledescription", "slide");
    s.setAttribute("aria-label", `${k + 1} of ${slides.length}: ${titleOf(s)}`);
    s.tabIndex = -1;
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = titleOf(s);
    if (s.classList.contains("section-slide") || k === 0) b.classList.add("is-section");
    b.addEventListener("click", () => { go(k); openToc(false); });
    li.appendChild(b);
    list.appendChild(li);
  });
  const tocButtons = [...list.querySelectorAll("button")];

  let current = -1;
  function go(n) {
    n = Math.max(0, Math.min(slides.length - 1, n));
    if (n === current) return;
    const moveFocus = current >= 0 && slides[current].contains(document.activeElement);
    slides.forEach((s, k) => {
      s.classList.toggle("active", k === n);
      s.classList.toggle("past", k < n);
      s.inert = k !== n;
    });
    current = n;
    const title = titleOf(slides[n]);
    titleEl.textContent = title;
    counter.textContent = `${n + 1} / ${slides.length}`;
    progress.style.width = `${((n + 1) / slides.length) * 100}%`;
    prevBtn.disabled = n === 0;
    nextBtn.disabled = n === slides.length - 1;
    tocButtons.forEach((b, k) => {
      b.classList.toggle("current", k === n);
      if (k === n) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    live.textContent = `Slide ${n + 1} of ${slides.length}: ${title}`;
    pointLectureAt(slides[n]);
    if (location.hash !== `#${n + 1}`) history.replaceState(null, "", `#${n + 1}`);
    if (moveFocus) slides[n].focus({ preventScroll: true });
  }

  function openToc(open = !toc.classList.contains("open")) {
    if (!open && toc.contains(document.activeElement)) tocBtn.focus({ preventScroll: true });
    toc.classList.toggle("open", open);
    toc.inert = !open;
    toc.setAttribute("aria-hidden", String(!open));
    tocBtn.setAttribute("aria-expanded", String(open));
    if (open) {
      tocButtons[current]?.focus({ preventScroll: true });
      tocButtons[current]?.scrollIntoView({ block: "center" });
    }
  }

  function fit() {
    const scale = Math.min(innerWidth / W, innerHeight / H) * 0.98;
    stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }

  prevBtn.addEventListener("click", () => go(current - 1));
  nextBtn.addEventListener("click", () => go(current + 1));
  tocBtn.addEventListener("click", () => openToc());

  addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest?.("input, textarea, select, [contenteditable]:not([contenteditable='false'])")) return;
    const k = e.key;
    if (k === "Escape") { openToc(false); return; }
    if (k === "c" || k === "C") { openToc(); return; }
    if (toc.classList.contains("open")) return;
    // Space must retain its native activation behavior on links and buttons.
    if (k === " " && e.target.closest?.("a, button, summary, [role='button']")) return;
    if (["ArrowRight", "ArrowDown", "PageDown"].includes(k) || (k === " " && !e.shiftKey)) { go(current + 1); e.preventDefault(); }
    else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(k) || (k === " " && e.shiftKey)) { go(current - 1); e.preventDefault(); }
    else if (k === "Home") { go(0); e.preventDefault(); }
    else if (k === "End") { go(slides.length - 1); e.preventDefault(); }
    else if (k === "f" || k === "F") {
      const action = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.();
      action?.catch(() => { /* Browser policies may disallow fullscreen; navigation still works. */ });
    }
    else if (k === "p" || k === "P") { print(); }
  });

  stage.addEventListener("click", (e) => {
    if (toc.classList.contains("open") && !e.target.closest?.(".toc, [data-act='toc']")) openToc(false);
  });
  addEventListener("focusin", (e) => {
    if (toc.classList.contains("open") && !toc.contains(e.target) && e.target !== tocBtn) openToc(false);
  });

  let touch = null;
  stage.addEventListener("touchstart", (e) => {
    touch = null;
    if (e.touches.length !== 1 || toc.classList.contains("open") || e.target.closest?.("a, button, input, textarea, select, pre, [contenteditable]")) return;
    touch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, { passive: true });
  stage.addEventListener("touchend", (e) => {
    if (!touch || !e.changedTouches.length) return;
    const dx = e.changedTouches[0].clientX - touch.x;
    const dy = e.changedTouches[0].clientY - touch.y;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.2) go(current + (dx < 0 ? 1 : -1));
    touch = null;
  });
  stage.addEventListener("touchcancel", () => { touch = null; });

  addEventListener("resize", fit);
  addEventListener("hashchange", () => go(parseInt(location.hash.slice(1), 10) - 1 || 0));

  // Light syntax highlighting for code blocks (Python, JSON, HTTP, HCL, shell).
  const KEYWORDS = /\b(def|async|await|return|for|in|if|else|elif|with|as|import|from|class|while|try|except|raise|lambda|yield|not|and|or|is|None|True|False|true|false|null|resource|variable|output|POST|GET)\b/;
  const TOKEN = new RegExp(
    [
      /(#[^\n]*)/.source,
      /("""[\s\S]*?"""|f?"(?:\\.|[^"\\\n])*"|f?'(?:\\.|[^'\\\n])*')/.source,
      KEYWORDS.source,
      /\b(\d+(?:\.\d+)?)\b/.source,
      /(@[\w.]+)/.source,
    ].join("|"),
    "g"
  );
  const escape = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  stage.querySelectorAll("pre.code code").forEach((el) => {
    const src = el.textContent.replace(/^\n/, "");
    let out = "";
    let last = 0;
    for (const m of src.matchAll(TOKEN)) {
      out += escape(src.slice(last, m.index));
      const cls = m[1] ? "t-c" : m[2] ? "t-s" : m[3] ? "t-k" : m[4] ? "t-n" : "t-b";
      out += `<span class="${cls}">${escape(m[0])}</span>`;
      last = m.index + m[0].length;
    }
    el.innerHTML = out + escape(src.slice(last));
  });

  fit();
  go((parseInt(location.hash.slice(1), 10) || 1) - 1);
  // Phones held upright: the 16:9 slide is too small to read. Offer the two ways out.
  if (weekFolder) {
    const hint = document.createElement("aside");
    hint.className = "deck-phone-hint";
    hint.innerHTML = `<p>Slides read best with the phone turned sideways.</p>
      <p><a href="${new URL(`${weekFolder}/docs/lecture.html`, courseRoot).href}">Read the lecture</a> · <a href="${home.href}">Course home</a></p>`;
    document.body.append(hint);
  }
  document.documentElement.classList.add("deck-ready");
})();
