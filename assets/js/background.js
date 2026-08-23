// 3D motion background: a rotating point cloud shaped into a torus knot ribbon and
// an orbiting particle shell, projected with perspective onto a 2D canvas. Depth
// drives size, brightness and draw order, so it reads as real geometry rather than
// scattered dots. No libraries, no WebGL - just the projection maths.
(function () {
  "use strict";

  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var canvas, ctx;
  var width = 0, height = 0, dpr = 1;
  var points = [], links = [];
  var rotation = { x: -0.35, y: 0, z: 0 };
  var pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  var palette = { a: [25, 227, 192], b: [154, 123, 255], c: [255, 180, 87] };
  var running = false;
  var FOCAL = 620;

  function readPalette() {
    var css = getComputedStyle(document.documentElement);
    palette.a = parseHex(css.getPropertyValue("--accent"), [25, 227, 192]);
    palette.b = parseHex(css.getPropertyValue("--accent-2"), [154, 123, 255]);
    palette.c = parseHex(css.getPropertyValue("--accent-3"), [255, 180, 87]);
  }

  function parseHex(value, fallback) {
    var hex = (value || "").trim().replace("#", "");
    if (hex.length === 3) hex = hex.replace(/./g, "$&$&");
    if (hex.length !== 6) return fallback;
    var int = parseInt(hex, 16);
    if (isNaN(int)) return fallback;
    return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
  }

  function rgba(colour, alpha) {
    return "rgba(" + colour[0] + "," + colour[1] + "," + colour[2] + "," + alpha.toFixed(3) + ")";
  }

  // A torus knot: the ribbon that gives the field a recognisable 3D form.
  function buildKnot(count, scale) {
    var built = [];
    for (var i = 0; i < count; i++) {
      var t = (i / count) * Math.PI * 2;
      var p = 2, q = 3;
      var r = Math.cos(q * t) + 2;
      built.push({
        x: scale * r * Math.cos(p * t) * 0.5,
        y: scale * r * Math.sin(p * t) * 0.5,
        z: scale * -Math.sin(q * t) * 0.5,
        size: 1.5,
        colour: "a",
        knot: i
      });
    }
    return built;
  }

  // A sphere of loose particles around the ribbon, placed on a Fibonacci lattice
  // so they spread evenly instead of clumping at the poles.
  function buildShell(count, radius) {
    var built = [];
    var golden = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < count; i++) {
      var y = 1 - (i / (count - 1)) * 2;
      var ring = Math.sqrt(Math.max(0, 1 - y * y));
      var theta = golden * i;
      var jitter = 0.82 + Math.random() * 0.3;
      built.push({
        x: Math.cos(theta) * ring * radius * jitter,
        y: y * radius * jitter,
        z: Math.sin(theta) * ring * radius * jitter,
        size: 0.7 + Math.random() * 1.3,
        colour: Math.random() < 0.12 ? "c" : "b"
      });
    }
    return built;
  }

  function build() {
    var scale = Math.min(width, height) * (width < 760 ? 0.42 : 0.34);
    var knot = buildKnot(width < 760 ? 130 : 220, scale);
    var shell = buildShell(width < 760 ? 60 : 120, scale * 1.5);
    points = knot.concat(shell);

    // Link consecutive ribbon points so the knot draws as a continuous strand.
    links = [];
    for (var i = 0; i < knot.length; i++) {
      links.push([i, (i + 1) % knot.length]);
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
    build();
  }

  function project(point) {
    var cosX = Math.cos(rotation.x), sinX = Math.sin(rotation.x);
    var cosY = Math.cos(rotation.y), sinY = Math.sin(rotation.y);

    // Rotate about Y, then X.
    var x = point.x * cosY - point.z * sinY;
    var z = point.x * sinY + point.z * cosY;
    var y = point.y * cosX - z * sinX;
    z = point.y * sinX + z * cosX;

    var depth = FOCAL / (FOCAL + z + 460);
    return {
      x: width / 2 + x * depth + pointer.x,
      y: height / 2 + y * depth + pointer.y,
      depth: depth,
      z: z
    };
  }

  function frame() {
    if (!running) return;

    rotation.y += 0.0022;
    rotation.x += 0.0006;
    pointer.x += (pointer.tx - pointer.x) * 0.04;
    pointer.y += (pointer.ty - pointer.y) * 0.04;

    ctx.clearRect(0, 0, width, height);

    var projected = points.map(project);

    // Strand first, so particles sit on top of it.
    ctx.lineWidth = 1.15;
    for (var l = 0; l < links.length; l++) {
      var a = projected[links[l][0]];
      var b = projected[links[l][1]];
      var span = Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
      if (span > 260) continue;
      var strength = Math.max(0, Math.min(1, (a.depth - 0.42) * 1.9));
      ctx.strokeStyle = rgba(palette.a, 0.05 + strength * 0.34);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    // Far points before near ones so depth reads correctly.
    var order = projected
      .map(function (p, index) { return { p: p, index: index }; })
      .sort(function (m, n) { return n.p.z - m.p.z; });

    for (var i = 0; i < order.length; i++) {
      var proj = order[i].p;
      var source = points[order[i].index];
      var fade = Math.max(0, Math.min(1, (proj.depth - 0.4) * 1.8));
      if (fade <= 0.02) continue;

      var radius = source.size * proj.depth * 1.9;
      ctx.fillStyle = rgba(palette[source.colour], 0.14 + fade * 0.7);
      ctx.beginPath();
      ctx.arc(proj.x, proj.y, radius, 0, Math.PI * 2);
      ctx.fill();

      // A soft halo on the nearest particles for a little bloom.
      if (fade > 0.82 && source.colour !== "a") {
        ctx.fillStyle = rgba(palette[source.colour], 0.07);
        ctx.beginPath();
        ctx.arc(proj.x, proj.y, radius * 3.4, 0, Math.PI * 2);
        ctx.fill();
      }
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

    readPalette();
    resize();
    start();

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 180);
    });

    window.addEventListener("pointermove", function (event) {
      pointer.tx = (event.clientX / window.innerWidth - 0.5) * 44;
      pointer.ty = (event.clientY / window.innerHeight - 0.5) * 34;
      rotation.z = pointer.tx * 0.0004;
    }, { passive: true });

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop(); else start();
    });

    var toggle = document.querySelector(".theme-toggle");
    if (toggle) toggle.addEventListener("click", function () { setTimeout(readPalette, 60); });
  });
})();
