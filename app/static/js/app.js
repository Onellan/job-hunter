/* Enhance server-rendered pages only after HTMX or Lucide has loaded. */

function renderIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

document.addEventListener("DOMContentLoaded", renderIcons);
document.addEventListener("htmx:afterSwap", renderIcons);
