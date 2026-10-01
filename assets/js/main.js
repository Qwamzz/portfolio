// Site behaviour: theme switch, mobile menu, nav hairline on scroll, reveal on scroll.
// Content is rendered on the server, so nothing here is required to read the page.
(function () {
  "use strict";

  var root = document.documentElement;

  document.addEventListener("DOMContentLoaded", function () {
    // ---------- Theme ----------
    var toggle = document.querySelector(".theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) { /* storage unavailable */ }
      });
    }

    // ---------- Mobile menu ----------
    var navToggle = document.querySelector(".nav-toggle");
    var menu = document.getElementById("mobile-menu");
    if (navToggle && menu) {
      navToggle.addEventListener("click", function () {
        var open = menu.hidden;
        menu.hidden = !open;
        navToggle.setAttribute("aria-expanded", String(open));
        navToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      });
    }

    // ---------- Hairline under the nav once the page scrolls ----------
    var nav = document.querySelector(".nav");
    if (nav) {
      var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }

    // ---------- Reveal ----------
    var items = document.querySelectorAll(".reveal");
    var show = function (el) { el.classList.add("in"); };

    if (!("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(items, show);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        show(entry.target);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });

    Array.prototype.forEach.call(items, function (el) { observer.observe(el); });

    // Anything already on screen is shown straight away, and a backstop makes
    // sure nothing stays hidden if the observer never fires.
    window.setTimeout(function () {
      Array.prototype.forEach.call(document.querySelectorAll(".reveal:not(.in)"), function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight) show(el);
      });
    }, 900);
  });
})();
