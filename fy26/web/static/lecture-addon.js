// Course website only: the lecture pages keep their own design; this adds the online harness
// to the materials bar that assets/lecture.js builds.
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
