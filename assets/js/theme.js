// Runs in <head> before first paint: marks JavaScript as available and applies the
// saved theme, or the system preference, so the page never flashes the wrong one.
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");
  var theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* storage unavailable */ }
  if (!theme && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) theme = "dark";
  if (theme) root.setAttribute("data-theme", theme);
})();
