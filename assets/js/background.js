// Motion background: a drifting constellation of nodes on a canvas behind the page,
// with a light parallax response to the pointer. Sits on top of the aurora gradient
// and the illustrated scene, below all content.
(function () {
  "use strict";

  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var canvas, ctx, nodes = [], width = 0, height = 0, dpr = 1;
  var pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  var colors = { line: "rgba(25,227,192,0.35)", dot: "rgba(154,123,255,0.75)" };
  var running = false;
  var LINK_DISTANCE = 148;

  function readColors() {
    var css = getComputedStyle(document.documentElement);
    var accent = (css.getPropertyValue("--accent") || "#19e3c0").trim();
    var accent2 = (css.getPropertyValue("--accent-2") || "#9a7bff").trim();
    colors.line = hexToRgba(accent, 0.34);
    colors.dot = hexToRgba(accent2, 0.75);
  }

  function hexToRgba(hex, alpha) {
    var value = hex.replace("#", "");
    if (value.length === 3) value = value.replace(/./g, "$&$&");
    var int = parseInt(value, 16);
    if (isNaN(int)) return "rgba(124,92,255," + alpha + ")";
    return "rgba(" + ((int >> 16) & 255) + "," + ((int >> 8) & 255) + "," + (int & 255) + "," + alpha + ")";
  }

  function nodeCount() {
    var area = window.innerWidth * window.innerHeight;
    return Math.max(22, Math.min(64, Math.round(area / 24000)));
  }

  function seed() {
    nodes = [];
    for (var i = 0; i < nodeCount(); i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        r: 1.1 + Math.random() * 2.1,
        depth: 0.4 + Math.random() * 0.8
      });
    }
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seed();
  }

  function frame() {
    if (!running) return;

    pointer.x += (pointer.tx - pointer.x) * 0.045;
    pointer.y += (pointer.ty - pointer.y) * 0.045;

    ctx.clearRect(0, 0, width, height);

    var i, j, a, b, dx, dy, distance;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      a.x += a.vx;
      a.y += a.vy;
      if (a.x < -40) a.x = width + 40;
      if (a.x > width + 40) a.x = -40;
      if (a.y < -40) a.y = height + 40;
      if (a.y > height + 40) a.y = -40;
    }

    ctx.lineWidth = 1;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        b = nodes[j];
        dx = a.x - b.x;
        dy = a.y - b.y;
        distance = Math.sqrt(dx * dx + dy * dy);
        if (distance > LINK_DISTANCE) continue;
        ctx.globalAlpha = (1 - distance / LINK_DISTANCE) * 0.75;
        ctx.strokeStyle = colors.line;
        ctx.beginPath();
        ctx.moveTo(a.x + pointer.x * a.depth, a.y + pointer.y * a.depth);
        ctx.lineTo(b.x + pointer.x * b.depth, b.y + pointer.y * b.depth);
        ctx.stroke();
      }
    }

    ctx.globalAlpha = 1;
    ctx.fillStyle = colors.dot;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      ctx.beginPath();
      ctx.arc(a.x + pointer.x * a.depth, a.y + pointer.y * a.depth, a.r, 0, Math.PI * 2);
      ctx.fill();
    }

    window.requestAnimationFrame(frame);
  }

  function start() {
    if (running || document.hidden) return;
    running = true;
    window.requestAnimationFrame(frame);
  }

  function stop() { running = false; }

  document.addEventListener("DOMContentLoaded", function () {
    canvas = document.createElement("canvas");
    canvas.className = "bg-canvas";
    canvas.setAttribute("aria-hidden", "true");
    document.body.appendChild(canvas);

    ctx = canvas.getContext("2d");
    if (!ctx) { canvas.remove(); return; }

    readColors();
    resize();
    start();

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 180);
    });

    window.addEventListener("pointermove", function (event) {
      pointer.tx = (event.clientX / window.innerWidth - 0.5) * 26;
      pointer.ty = (event.clientY / window.innerHeight - 0.5) * 26;
    }, { passive: true });

    // Stop burning cycles when the tab is in the background.
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop(); else start();
    });

    // Node colours follow the theme.
    var toggle = document.querySelector(".theme-toggle");
    if (toggle) toggle.addEventListener("click", function () { setTimeout(readColors, 60); });
  });
})();
