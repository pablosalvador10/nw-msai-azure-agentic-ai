// Course website only (served by web/main.py), after assets/lecture.js:
// adds the online harness to the materials bar, and draws Mermaid diagrams when the page has any.
"use strict";

(() => {
  const bar = document.querySelector(".materials-nav");
  if (bar && !bar.querySelector('a[href="/score/"]')) {
    const link = document.createElement("a");
    link.href = "/score/";
    link.textContent = "Score your service";
    link.title = "Run the harness against your deployed service";
    bar.append(link);
  }

  const bundle = document.currentScript?.dataset.mermaid;
  const diagrams = [...document.querySelectorAll("pre.mermaid")];
  if (bundle && diagrams.length) {
    const script = document.createElement("script");
    script.src = bundle;
    script.onload = () => {
      const { mermaid } = window;
      if (!mermaid) return;
      mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
      mermaid.run({ nodes: diagrams }).catch(() => {
        // A diagram that fails to parse stays readable as its source text.
      });
    };
    document.head.append(script);
  }
})();
