// Rebuilds the certifications page from /api/certifications so entries added
// through /admin show up without a redeploy. The server-rendered markup stays
// as the fallback if the request fails or JavaScript is unavailable.
(function () {
  "use strict";

  var BLURBS = {
    "Microsoft": "Architecture, DevOps, security, networking and AI across the Azure platform.",
    "Cloud & Cloud Native": "Multi-cloud and container platform credentials.",
    "Security & Standards": "Audit standards and information security credentials.",
    "Other": "Foundational technical training."
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function cardFor(item) {
    var card = el("div", "card cert reveal");
    card.appendChild(el("span", "cert-code", item.code || "CERT"));

    var body = el("div");
    body.appendChild(el("strong", null, item.name));

    var bits = [item.issuer, item.note].filter(Boolean).join(" · ");
    if (bits) body.appendChild(el("span", null, bits));

    if (item.file || item.url) {
      var links = el("span", "cert-links");
      if (item.file) {
        var file = el("a", null, "View certificate");
        file.href = item.file;
        file.target = "_blank";
        file.rel = "noopener";
        links.appendChild(file);
      }
      if (item.url) {
        var verify = el("a", null, "Verify");
        verify.href = item.url;
        verify.target = "_blank";
        verify.rel = "noopener";
        links.appendChild(verify);
      }
      body.appendChild(links);
    }

    card.appendChild(body);
    return card;
  }

  function sectionFor(category, items, index) {
    var section = el("section", "section" + (index % 2 ? " alt" : ""));
    var wrap = el("div", "wrap");

    var head = el("div", "section-head");
    head.appendChild(el("h2", null, category));
    head.appendChild(el("p", null, BLURBS[category] || ""));
    wrap.appendChild(head);

    var grid = el("div", "grid " + (items.length > 2 ? "grid-3" : "grid-2"));
    items.forEach(function (item) { grid.appendChild(cardFor(item)); });
    wrap.appendChild(grid);

    section.appendChild(wrap);
    return section;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("cert-root");
    if (!root) return;

    fetch("/api/certifications", { credentials: "same-origin" })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(); })
      .then(function (data) {
        if (!data.items || !data.items.length) return;

        var order = data.categories || [];
        var grouped = {};
        data.items.forEach(function (item) {
          var key = item.category || "Other";
          (grouped[key] = grouped[key] || []).push(item);
        });

        Object.keys(grouped).forEach(function (key) {
          if (order.indexOf(key) === -1) order.push(key);
        });

        root.innerHTML = "";
        var index = 0;
        order.forEach(function (category) {
          if (!grouped[category]) return;
          root.appendChild(sectionFor(category, grouped[category], index));
          index += 1;
        });

        // The reveal observer ran before these nodes existed.
        Array.prototype.forEach.call(root.querySelectorAll(".reveal"), function (node) {
          node.classList.add("in");
        });
      })
      .catch(function () { /* keep the fallback markup */ });
  });
})();
