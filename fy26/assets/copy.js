/* Copy buttons for example prompts. Progressive enhancement: without JavaScript the buttons stay hidden. */
(() => {
  if (!navigator.clipboard) return;
  for (const button of document.querySelectorAll("button.copy[data-copy]")) {
    button.hidden = false;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select it";
      }
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1600);
    });
  }
})();
