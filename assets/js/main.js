// Portfolio interactions: theme, mobile nav, accordions, scroll reveal.
(function () {
  "use strict";

  // ---------- Theme ----------
  var root = document.documentElement;
  var stored = null;
  try { stored = localStorage.getItem("theme"); } catch (e) { /* private mode */ }
  if (!stored && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    stored = "dark";
  }
  if (stored) root.setAttribute("data-theme", stored);

  function paintToggle(btn) {
    var dark = root.getAttribute("data-theme") === "dark";
    btn.textContent = dark ? "☀" : "☾";
    btn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.querySelector(".theme-toggle");
    if (toggle) {
      paintToggle(toggle);
      toggle.addEventListener("click", function () {
        var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
        paintToggle(toggle);
      });
    }

    // ---------- Mobile navigation ----------
    var navToggle = document.querySelector(".nav-toggle");
    var navLinks = document.querySelector(".nav-links");
    if (navToggle && navLinks) {
      navToggle.addEventListener("click", function () {
        var open = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", String(open));
      });
    }

    // ---------- Active link ----------
    var page = location.pathname.split("/").pop() || "index.html";
    Array.prototype.forEach.call(document.querySelectorAll(".nav-links a"), function (a) {
      var href = a.getAttribute("href");
      if (href === page || (page === "" && href === "index.html")) a.classList.add("active");
    });

    // ---------- Accordions ----------
    Array.prototype.forEach.call(document.querySelectorAll(".acc-btn"), function (btn) {
      btn.addEventListener("click", function () {
        var body = document.getElementById(btn.getAttribute("aria-controls"));
        if (!body) return;
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", String(!open));
        body.hidden = open;
      });
    });

    // ---------- Scroll reveal ----------
    var items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(items, function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -60px 0px", threshold: 0.08 });
    Array.prototype.forEach.call(items, function (el) { io.observe(el); });

    // Safety net: if the observer never fires (some embedded or throttled browsers),
    // show anything that is already on screen rather than leaving it invisible.
    setTimeout(function () {
      Array.prototype.forEach.call(document.querySelectorAll(".reveal:not(.in)"), function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add("in");
      });
    }, 1200);
  });

  // ---------- Footer year ----------
  document.addEventListener("DOMContentLoaded", function () {
    var y = document.querySelector("[data-year]");
    if (y) y.textContent = String(new Date().getFullYear());
  });
})();
