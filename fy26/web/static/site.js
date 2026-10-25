// The course website shell: navigation drawer, "on this page", code highlighting and copy,
// diagrams, search (Ctrl/Cmd+K or /), and "continue where you left off".
// Text from course files is written with textContent; nothing here builds HTML from strings it did not escape.
"use strict";

(() => {
  const script = document.currentScript;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
  };

  // ---------------------------------------------------------------- navigation drawer (small screens)
  const toggle = $(".nav-toggle");
  const setNav = (open) => {
    document.body.classList.toggle("nav-open", open);
    toggle?.setAttribute("aria-expanded", String(open));
    toggle?.setAttribute("aria-label", open ? "Close course navigation" : "Open course navigation");
  };
  toggle?.addEventListener("click", () => setNav(!document.body.classList.contains("nav-open")));
  $$("[data-nav-close]").forEach((el) => el.addEventListener("click", () => setNav(false)));
  addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
      setNav(false);
      toggle?.focus();
    }
  });
  const nav = $(".site-nav");
  const current = $("[aria-current=page]", nav || document);
  if (nav && current && (current.offsetTop > nav.clientHeight - 80)) nav.scrollTop = current.offsetTop - nav.clientHeight / 3;

  // ---------------------------------------------------------------- account menu
  const account = $(".account");
  document.addEventListener("click", (event) => {
    if (account?.open && !account.contains(event.target)) account.open = false;
  });

  // ---------------------------------------------------------------- on this page
  const toc = $(".doc-toc");
  const heads = $$(".prose h2[id], .prose h3[id]");
  if (toc && heads.length >= 2) {
    const title = document.createElement("p");
    title.className = "doc-toc__title";
    title.textContent = "On this page";
    toc.append(title);
    const links = heads.map((head) => {
      const link = document.createElement("a");
      link.href = `#${head.id}`;
      link.textContent = head.textContent;
      if (head.tagName === "H3") link.className = "sub";
      toc.append(link);
      return link;
    });
    const top = document.createElement("a");
    top.href = "#main";
    top.className = "doc-toc__top";
    top.textContent = "Back to top ↑";
    toc.append(top);
    let ticking = false;
    const spy = () => {
      ticking = false;
      let active = 0;
      heads.forEach((head, i) => { if (head.getBoundingClientRect().top < 140) active = i; });
      links.forEach((link, i) => link.classList.toggle("active", i === active));
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, { passive: true });
    spy();
  } else {
    toc?.remove();
  }

  // ---------------------------------------------------------------- code: light highlighting and copy
  const KEYWORDS = /\b(def|async|await|return|for|in|if|else|elif|with|as|import|from|class|while|try|except|finally|raise|lambda|yield|not|and|or|is|None|True|False|true|false|null|resource|variable|output|locals|module|provider|data|POST|GET)\b/;
  const TOKEN = new RegExp(
    [
      /(#[^\n]*)/.source,
      /("""[\s\S]*?"""|f?"(?:\\.|[^"\\\n])*"|f?'(?:\\.|[^'\\\n])*')/.source,
      KEYWORDS.source,
      /\b(\d+(?:\.\d+)?)\b/.source,
      /(@[\w.]+)/.source,
    ].join("|"),
    "g",
  );
  const CLASSES = ["t-c", "t-s", "t-k", "t-n", "t-b"];
  for (const code of $$("pre.code:not([data-plain]) code")) {
    const src = code.textContent;
    if (src.length > 200000) continue;
    const out = document.createDocumentFragment();
    let last = 0;
    for (const m of src.matchAll(TOKEN)) {
      if (m.index > last) out.append(src.slice(last, m.index));
      const span = document.createElement("span");
      span.className = CLASSES[m.slice(1).findIndex((group) => group !== undefined)] || "t-b";
      span.textContent = m[0];
      out.append(span);
      last = m.index + m[0].length;
    }
    out.append(src.slice(last));
    code.replaceChildren(out);
  }
  for (const pre of $$("pre.code")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-btn";
    button.textContent = "Copy";
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText($("code", pre).textContent);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select and copy";
      }
      setTimeout(() => { button.textContent = "Copy"; }, 1600);
    });
    pre.append(button);
  }

  // ---------------------------------------------------------------- diagrams
  const bundle = script?.dataset.mermaid;
  const diagrams = $$("pre.mermaid");
  if (bundle && diagrams.length) {
    const loader = document.createElement("script");
    loader.src = bundle;
    loader.onload = () => {
      const { mermaid } = window;
      if (!mermaid) return;
      mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral", fontFamily: "inherit" });
      mermaid.run({ nodes: diagrams }).catch(() => { /* a diagram that fails to parse stays readable as text */ });
    };
    document.head.append(loader);
  }

  // ---------------------------------------------------------------- continue where you left off
  const article = $("article[data-track]");
  if (article) store.set("lastVisit", { t: article.dataset.track, u: location.pathname });
  const resume = $(".continue");
  const last = store.get("lastVisit");
  if (resume && last && typeof last.u === "string" && last.u.startsWith("/") && !last.u.startsWith("//")) {
    const link = $("a", resume);
    link.href = last.u;
    link.textContent = String(last.t || last.u);
    resume.hidden = false;
  }

  // ---------------------------------------------------------------- search
  const dialog = $("dialog.search");
  const input = $(".search__input", dialog || document);
  const list = $(".search__results", dialog || document);
  let index = null;
  let results = [];
  let selected = 0;

  const loadIndex = async () => {
    if (index) return index;
    try {
      const response = await fetch("/_site/search.json", { credentials: "same-origin" });
      index = response.ok ? await response.json() : [];
    } catch {
      index = [];
    }
    return index;
  };

  const marked = (text, words) => {
    const fragment = document.createDocumentFragment();
    const lower = text.toLowerCase();
    let i = 0;
    while (i < text.length) {
      let hit = null;
      for (const word of words) {
        const at = lower.indexOf(word, i);
        if (at !== -1 && (!hit || at < hit[0])) hit = [at, word.length];
      }
      if (!hit) break;
      if (hit[0] > i) fragment.append(text.slice(i, hit[0]));
      const mark = document.createElement("mark");
      mark.textContent = text.slice(hit[0], hit[0] + hit[1]);
      fragment.append(mark);
      i = hit[0] + hit[1];
    }
    fragment.append(text.slice(i));
    return fragment;
  };

  const search = (query) => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length || !index) return [];
    const found = [];
    for (const page of index) {
      const title = page.t.toLowerCase();
      const haystack = `${title} ${page.k.toLowerCase()}`;
      if (words.every((w) => haystack.includes(w))) {
        found.push({ title: page.t, sub: page.k, url: page.u, score: (title.startsWith(words[0]) ? 120 : 100) - title.length / 100 });
      }
      for (const [heading, anchor] of page.h) {
        const text = heading.toLowerCase();
        if (words.every((w) => text.includes(w) || title.includes(w)) && words.some((w) => text.includes(w))) {
          found.push({ title: heading, sub: page.t, url: `${page.u}#${anchor}`, score: 60 - text.length / 100 });
        }
      }
    }
    return found.sort((a, b) => b.score - a.score).slice(0, 14);
  };

  const render = () => {
    const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    list.replaceChildren();
    if (!words.length) return;
    if (!results.length) {
      const empty = document.createElement("li");
      empty.className = "search__empty";
      empty.textContent = `No results for "${input.value.trim()}".`;
      list.append(empty);
      return;
    }
    results.forEach((result, i) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = result.url;
      link.setAttribute("role", "option");
      link.setAttribute("aria-selected", String(i === selected));
      const title = document.createElement("span");
      title.className = "r-title";
      title.append(marked(result.title, words));
      const sub = document.createElement("span");
      sub.className = "r-sub";
      sub.textContent = result.sub;
      link.append(title, sub);
      link.addEventListener("mousemove", () => { if (selected !== i) { selected = i; render(); } });
      item.append(link);
      list.append(item);
    });
    list.children[selected]?.scrollIntoView({ block: "nearest" });
  };

  const open = async () => {
    if (!dialog || dialog.open) return;
    dialog.showModal();
    input.value = "";
    results = [];
    render();
    input.focus();
    await loadIndex();
  };

  $$("[data-search-open]").forEach((el) => el.addEventListener("click", open));
  addEventListener("keydown", (event) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) || event.target.isContentEditable;
    if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
      event.preventDefault();
      open();
    }
  });
  input?.addEventListener("input", async () => {
    await loadIndex();
    results = search(input.value);
    selected = 0;
    render();
  });
  input?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!results.length) return;
      selected = (selected + (event.key === "ArrowDown" ? 1 : -1) + results.length) % results.length;
      render();
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (results[selected]) location.href = results[selected].url;
    }
  });
  dialog?.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  const mac = /Mac|iPhone|iPad/.test(navigator.platform);
  $$(".search-trigger kbd").forEach((kbd) => { kbd.textContent = mac ? "⌘K" : "Ctrl K"; });
})();
