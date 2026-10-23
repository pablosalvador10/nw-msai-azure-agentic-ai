/* Weekly guides: contents column, reading progress, back to top, print, light code highlighting. */
(() => {
  const scriptURL = document.currentScript?.src;
  const courseRoot = scriptURL ? new URL("../", scriptURL) : null;
  const weekFolder = decodeURIComponent(location.pathname).match(/\/(week\d{2}-[^/]+)\//)?.[1];
  const brand = document.querySelector(".brand-copy");
  if (brand && courseRoot) {
    const home = document.createElement("a");
    home.href = new URL("index.html", courseRoot).href;
    home.className = "course-home-link";
    home.setAttribute("aria-label", "Course home · Agentic AI on Microsoft Foundry");
    home.append(...brand.childNodes);
    brand.append(home);
  }
  if (weekFolder && courseRoot && document.querySelector(".topbar")) {
    const weekRoot = new URL(`${weekFolder}/`, courseRoot);
    const materials = document.createElement("nav");
    materials.className = "materials-nav";
    materials.setAttribute("aria-label", "Learning materials");
    for (const [label, path] of [["Course home", "../../index.html"], ["Weekly overview", "../README.md"], ["Lecture", "lecture.html"], ["Slides", "slides.html"], ["Main lab · VS Code", "../lab.ipynb"], ["Optional deep dive", "../deep-dive.ipynb"]]) {
      const link = document.createElement("a");
      link.textContent = label;
      link.href = new URL(path, new URL("docs/", weekRoot)).href;
      if (link.pathname === location.pathname) link.setAttribute("aria-current", "page");
      if (path.endsWith(".ipynb")) link.title = "Open this notebook in VS Code; browsers may download it.";
      materials.append(link);
    }
    document.querySelector(".topbar").after(materials);
  }
  const nav = document.querySelector(".toc");
  const sections = [...document.querySelectorAll("main section[id]")];
  const compact = matchMedia("(max-width: 1000px)");
  let contents = null;
  if (nav) {
    const label = document.createElement("p");
    label.className = "toc__label";
    label.textContent = "Contents";
    nav.append(label);
    let group = null;
    for (const section of sections) {
      if (section.dataset.group && section.dataset.group !== group) {
        group = section.dataset.group;
        const heading = document.createElement("p");
        heading.className = "toc__group";
        heading.textContent = group;
        nav.append(heading);
      }
      const h2 = section.querySelector("h2");
      const link = document.createElement("a");
      link.href = `#${section.id}`;
      link.textContent = section.dataset.toc || (h2 ? h2.textContent : section.id);
      nav.append(link);
      for (const h3 of section.querySelectorAll("h3[id]")) {
        const sub = document.createElement("a");
        sub.href = `#${h3.id}`;
        sub.className = "sub";
        sub.textContent = h3.dataset.toc || h3.textContent;
        nav.append(sub);
      }
    }
    // One native disclosure keeps the same links available on smaller screens.
    contents = document.createElement("details");
    contents.className = "toc-disclosure";
    const summary = document.createElement("summary");
    summary.textContent = "Contents";
    nav.before(contents);
    contents.append(summary, nav);
    contents.open = !compact.matches;
    compact.addEventListener("change", () => {
      if (compact.matches && nav.contains(document.activeElement)) summary.focus({ preventScroll: true });
      contents.open = !compact.matches;
    });
    contents.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && compact.matches && contents.open) {
        summary.focus({ preventScroll: true });
        contents.open = false;
      }
    });
    nav.addEventListener("click", (event) => {
      const link = event.target.closest?.("a[href^='#']");
      if (!link || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || event.button !== 0) return;
      const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      if (!target) return;
      event.preventDefault();
      if (compact.matches) contents.open = false;
      if (!target.hasAttribute("tabindex")) target.tabIndex = -1;
      target.focus({ preventScroll: true });
      if (location.hash !== link.hash) history.pushState(null, "", link.hash);
      target.scrollIntoView({ block: "start" });
      onScroll();
    });
  }

  const progress = document.getElementById("progress");
  const top = document.getElementById("back-to-top");
  const links = [...document.querySelectorAll(".toc a")];
  const targets = links.map((link) => document.getElementById(decodeURIComponent(link.hash.slice(1))));
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    if (progress) progress.style.width = (max > 0 ? Math.max(0, Math.min(100, (scrollY / max) * 100)) : 0) + "%";
    if (top) {
      const visible = scrollY > 900;
      top.classList.toggle("visible", visible);
      top.inert = !visible;
      top.setAttribute("aria-hidden", String(!visible));
    }
    let current = 0;
    targets.forEach((el, index) => { if (el && el.getBoundingClientRect().top < 140) current = index; });
    links.forEach((link, index) => {
      link.classList.toggle("active", index === current);
      if (index === current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
    const active = links[current];
    if (active && nav && !compact.matches && (active.offsetTop < nav.scrollTop || active.offsetTop > nav.scrollTop + nav.clientHeight - 40)) {
      nav.scrollTop = active.offsetTop - nav.clientHeight / 3;
    }
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  top?.addEventListener("click", () => {
    document.querySelector("main")?.focus({ preventScroll: true });
    scrollTo({ top: 0 });
  });
  document.getElementById("print")?.addEventListener("click", () => print());

  // Light syntax highlighting for Python, JSON, HTTP, HCL and shell. Blocks marked data-plain are left alone.
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
  document.querySelectorAll("pre.code:not([data-plain]) code").forEach((el) => {
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

  const scrollAreas = [...document.querySelectorAll(".code, .table-wrap, .diagram, .formula")].map((element) => ({
    element,
    tabindex: element.getAttribute("tabindex"),
    role: element.getAttribute("role"),
    label: element.getAttribute("aria-label"),
  }));
  function updateLayout() {
    const header = document.querySelector(".topbar");
    if (header) document.documentElement.style.setProperty("--topbar-height", `${header.getBoundingClientRect().height}px`);
    for (const { element, tabindex, role, label } of scrollAreas) {
      const overflow = element.scrollWidth > element.clientWidth + 2;
      const name = element.matches(".code") ? "Code example" : element.matches(".table-wrap") ? "Table" : element.matches(".diagram") ? "Diagram" : "Formula";
      const values = {
        tabindex: overflow ? "0" : tabindex,
        role: role || (overflow ? "region" : null),
        "aria-label": label || (overflow ? `${name} (scroll horizontally)` : null),
      };
      for (const [attribute, value] of Object.entries(values)) {
        if (value === null) element.removeAttribute(attribute);
        else element.setAttribute(attribute, value);
      }
    }
    onScroll();
  }
  addEventListener("resize", updateLayout);
  addEventListener("load", updateLayout);
  updateLayout();
})();
