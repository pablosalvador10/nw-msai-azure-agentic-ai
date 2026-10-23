// Course website only (served by web/main.py): add the online harness to a lecture's materials bar.
"use strict";

(() => {
  const bar = document.querySelector(".materials-nav");
  if (!bar || bar.querySelector('a[href="/score/"]')) return;
  const link = document.createElement("a");
  link.href = "/score/";
  link.textContent = "Score your service";
  link.title = "Run the harness against your deployed service";
  bar.append(link);
})();
