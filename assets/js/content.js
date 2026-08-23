// Renders every editable section from /api/content so edits made at /admin appear
// without a redeploy. The HTML shipped with the page is the fallback: if the
// request fails, or a collection is empty, the original markup stays put.
(function () {
  "use strict";

  var CERT_BLURBS = {
    "Microsoft": "Architecture, DevOps, security, networking and AI across the Azure platform.",
    "Cloud & Cloud Native": "Multi-cloud and container platform credentials.",
    "Security & Standards": "Audit standards and information security credentials.",
    "Other": "Foundational technical training."
  };
  var CERT_ORDER = ["Microsoft", "Cloud & Cloud Native", "Security & Standards", "Other"];
  var EXPERIENCE_GROUPS = ["Cloud Engineering", "Data & AI", "Earlier Roles"];

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function link(href, text, className) {
    var a = el("a", className, text);
    a.href = href;
    if (/^https?:/.test(href)) { a.target = "_blank"; a.rel = "noopener"; }
    return a;
  }

  function bulletList(items) {
    var ul = el("ul", "bullets");
    (items || []).forEach(function (line) { ul.appendChild(el("li", null, line)); });
    return ul;
  }

  function paragraphs(parent, body) {
    (body || "").split(/\n\s*\n/).forEach(function (chunk) {
      if (chunk.trim()) parent.appendChild(el("p", null, chunk.trim()));
    });
  }

  function fill(id, value) {
    var node = document.getElementById(id);
    if (node && value) node.textContent = value;
  }

  function replace(id, nodes) {
    var root = document.getElementById(id);
    if (!root || !nodes.length) return;
    root.innerHTML = "";
    nodes.forEach(function (node) { root.appendChild(node); });
    Array.prototype.forEach.call(root.querySelectorAll(".reveal"), function (node) {
      node.classList.add("in");
    });
  }

  // ---------- Home ----------
  function renderHome(content) {
    var profile = (content.profile || [])[0];
    if (profile) {
      fill("p-name", profile.name);
      fill("p-tagline", profile.tagline);
      fill("p-lede", profile.lede);
    }

    replace("stats-root", (content.stats || []).map(function (item) {
      var card = el("div", "stat reveal");
      card.appendChild(el("b", null, item.value));
      card.appendChild(el("span", null, item.label));
      return card;
    }));

    replace("skills-root", (content.skills || []).map(function (item, index) {
      var row = el("div", "skill-row reveal" + (index % 2 ? " flip" : ""));

      var art = el("div", "skill-art");
      var img = document.createElement("img");
      img.src = item.image || "assets/img/cloud-hero.svg";
      img.alt = "";
      art.appendChild(img);
      row.appendChild(art);

      var body = el("div");
      body.appendChild(el("h3", null, item.title));

      if ((item.tags || []).length) {
        var tags = el("div", "skill-tags");
        item.tags.forEach(function (tag) { tags.appendChild(el("span", "tag", tag)); });
        body.appendChild(tags);
      }
      body.appendChild(bulletList(item.bullets));
      row.appendChild(body);
      return row;
    }));
  }

  // ---------- Education ----------
  function renderEducation(content) {
    replace("edu-root", (content.education || []).map(function (item) {
      var wrap = el("div", "edu reveal");
      wrap.appendChild(el("div", "edu-badge", item.badge || "•"));

      var body = el("div");
      var top = el("div", "job-top");
      var left = el("div");
      left.appendChild(el("h3", null, item.degree));
      left.appendChild(el("div", "org", item.school));
      top.appendChild(left);
      top.appendChild(el("div", "when", item.period));
      body.appendChild(top);
      body.appendChild(bulletList(item.bullets));

      wrap.appendChild(body);
      return wrap;
    }));

    replace("extras-root", (content.extras || []).map(function (item) {
      var card = el("article", "card reveal");
      card.appendChild(el("h3", null, item.title));
      paragraphs(card, item.body);
      if (item.link_url && item.link_label) {
        var meta = el("p", "meta");
        meta.appendChild(link(item.link_url, item.link_label));
        card.appendChild(meta);
      }
      return card;
    }));
  }

  // ---------- Experience ----------
  function renderExperience(content) {
    var roles = content.experience || [];
    if (!roles.length) return;

    var groups = {};
    roles.forEach(function (role) {
      var key = role.group || EXPERIENCE_GROUPS[0];
      (groups[key] = groups[key] || []).push(role);
    });

    var order = EXPERIENCE_GROUPS.filter(function (name) { return groups[name]; });
    Object.keys(groups).forEach(function (name) {
      if (order.indexOf(name) === -1) order.push(name);
    });

    replace("exp-root", order.map(function (name, index) {
      var block = el("div", "acc");
      var id = "acc-" + index;

      var button = el("button", "acc-btn");
      button.type = "button";
      button.setAttribute("aria-expanded", index === 0 ? "true" : "false");
      button.setAttribute("aria-controls", id);
      button.appendChild(el("span", null, name));
      button.appendChild(el("span", "chev", "▾"));

      var body = el("div", "acc-body");
      body.id = id;
      if (index !== 0) body.hidden = true;

      var timeline = el("ul", "timeline");
      groups[name].forEach(function (role) {
        var li = el("li");
        var job = el("div", "job");

        var top = el("div", "job-top");
        var left = el("div");
        left.appendChild(el("h3", null, role.role));
        left.appendChild(el("div", "org", role.org));
        top.appendChild(left);
        top.appendChild(el("div", "when", role.period));

        job.appendChild(top);
        job.appendChild(bulletList(role.bullets));
        li.appendChild(job);
        timeline.appendChild(li);
      });
      body.appendChild(timeline);

      button.addEventListener("click", function () {
        var open = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", String(!open));
        body.hidden = open;
      });

      block.appendChild(button);
      block.appendChild(body);
      return block;
    }));
  }

  // ---------- Projects ----------
  function renderProjects(content) {
    replace("projects-root", (content.projects || []).map(function (item) {
      var card = el("article", "card reveal");
      card.appendChild(el("h3", null, item.title));
      paragraphs(card, item.body);
      if (item.meta) card.appendChild(el("p", "meta", item.meta));
      return card;
    }));

    replace("repos-root", (content.repos || []).map(function (item) {
      var card = link(item.url, null, "card repo reveal");

      var name = el("span", "repo-name");
      var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      icon.setAttribute("viewBox", "0 0 24 24");
      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.9 10.9c.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.4-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.8-1.6-2.6-.3-5.3-1.3-5.3-5.8 0-1.3.5-2.3 1.2-3.2 0-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.4 11.4 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.6.2 2.8.1 3.1.8.9 1.2 1.9 1.2 3.2 0 4.5-2.7 5.5-5.3 5.8.4.4.8 1.1.8 2.2v3.2c0 .4.2.7.8.6A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5z");
      icon.appendChild(path);
      name.appendChild(icon);
      name.appendChild(document.createTextNode(item.name));
      card.appendChild(name);

      card.appendChild(el("p", null, item.description));

      var foot = el("span", "repo-foot");
      var lang = el("span", "lang");
      lang.appendChild(el("i", "dot"));
      lang.appendChild(document.createTextNode(item.lang || "Repository"));
      foot.appendChild(lang);
      foot.appendChild(el("span", "repo-link", "View repo →"));
      card.appendChild(foot);

      return card;
    }));

    replace("writing-root", (content.writing || []).map(function (item) {
      var card = el("article", "card reveal");
      card.appendChild(el("h3", null, item.title));
      paragraphs(card, item.body);
      if (item.link_url) {
        var meta = el("p", "meta");
        meta.appendChild(link(item.link_url, item.link_label || item.link_url));
        card.appendChild(meta);
      }
      return card;
    }));
  }

  // ---------- Certifications ----------
  function renderCertifications(content) {
    var items = content.certifications || [];
    var root = document.getElementById("cert-root");

    if (root && items.length) {
      var grouped = {};
      items.forEach(function (item) {
        var key = item.category || "Other";
        (grouped[key] = grouped[key] || []).push(item);
      });

      var order = CERT_ORDER.filter(function (name) { return grouped[name]; });
      Object.keys(grouped).forEach(function (name) {
        if (order.indexOf(name) === -1) order.push(name);
      });

      root.innerHTML = "";
      order.forEach(function (category, index) {
        var section = el("section", "section" + (index % 2 ? " alt" : ""));
        var wrap = el("div", "wrap");

        var head = el("div", "section-head");
        head.appendChild(el("h2", null, category));
        head.appendChild(el("p", null, CERT_BLURBS[category] || ""));
        wrap.appendChild(head);

        var list = grouped[category];
        var grid = el("div", "grid " + (list.length > 2 ? "grid-3" : "grid-2"));
        list.forEach(function (item) {
          var card = el("div", "card cert reveal in");
          card.appendChild(el("span", "cert-code", item.code || "CERT"));

          var body = el("div");
          body.appendChild(el("strong", null, item.name));
          var bits = [item.issuer, item.note].filter(Boolean).join(" · ");
          if (bits) body.appendChild(el("span", null, bits));

          if (item.file || item.url) {
            var links = el("span", "cert-links");
            if (item.file) links.appendChild(link(item.file, "View certificate"));
            if (item.url) links.appendChild(link(item.url, "Verify"));
            body.appendChild(links);
          }

          card.appendChild(body);
          grid.appendChild(card);
        });

        wrap.appendChild(grid);
        section.appendChild(wrap);
        root.appendChild(section);
      });
    }

    replace("recognition-root", (content.recognition || []).map(function (item) {
      var card = el("article", "card reveal");
      card.appendChild(el("h3", null, item.title));
      paragraphs(card, item.body);
      return card;
    }));
  }

  // ---------- Contact ----------
  function renderContact(content) {
    var details = (content.contact || [])[0];
    if (details) {
      fill("c-lede", details.lede);

      var root = document.getElementById("contact-root");
      if (root) {
        var rows = [];
        if (details.email) rows.push(["mailto:" + details.email, details.email, "M2 4h20a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm10 9L2.2 6.4 2 6.5V7l10 6.7L22 7v-.5l-.2-.1z"]);
        if (details.phone) rows.push([details.phone_link || "tel:" + details.phone.replace(/\s+/g, ""), details.phone, "M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .6 3.6 1 1 0 0 1-.25 1z"]);
        if (details.location) rows.push([null, details.location, "M12 2a7 7 0 0 1 7 7c0 5.2-7 13-7 13S5 14.2 5 9a7 7 0 0 1 7-7zm0 9.5A2.5 2.5 0 1 0 12 6.5a2.5 2.5 0 0 0 0 5z"]);

        if (rows.length) {
          root.innerHTML = "";
          rows.forEach(function (row) {
            var li = el("li");
            var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            icon.setAttribute("viewBox", "0 0 24 24");
            var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", row[2]);
            icon.appendChild(path);
            li.appendChild(icon);
            li.appendChild(row[0] ? link(row[0], row[1]) : el("span", null, row[1]));
            root.appendChild(li);
          });
        }

        var mailButton = document.querySelector('.hero-actions a[href^="mailto:"]');
        if (mailButton && details.email) mailButton.href = "mailto:" + details.email;
      }
    }

    replace("services-root", (content.services || []).map(function (item) {
      var card = el("article", "card reveal");
      card.appendChild(el("h3", null, item.title));
      paragraphs(card, item.body);
      return card;
    }));
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("/api/content", { credentials: "same-origin" })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(); })
      .then(function (data) {
        var content = data.content || {};
        renderHome(content);
        renderEducation(content);
        renderExperience(content);
        renderProjects(content);
        renderCertifications(content);
        renderContact(content);
      })
      .catch(function () { /* keep the markup already on the page */ });
  });
})();
