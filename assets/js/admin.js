// Certifications admin: sign in, add, delete. Talks to the JSON API in app.py.
(function () {
  "use strict";

  var msgEl, listEl, countEl, panel, loginCard, disabledCard;

  function say(text, isError) {
    msgEl.textContent = text || "";
    msgEl.className = "admin-msg" + (text ? (isError ? " error" : " ok") : "");
    if (text && !isError) setTimeout(function () { if (msgEl.textContent === text) say(""); }, 4000);
  }

  function show(el, visible) { el.hidden = !visible; }

  function api(url, options) {
    return fetch(url, Object.assign({ credentials: "same-origin" }, options || {}))
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          if (!response.ok) throw new Error(body.error || ("Request failed (" + response.status + ")"));
          return body;
        });
      });
  }

  function render(data) {
    var select = document.getElementById("category");
    if (select && !select.options.length) {
      data.categories.forEach(function (name) {
        var option = document.createElement("option");
        option.value = option.textContent = name;
        select.appendChild(option);
      });
    }

    countEl.textContent = String(data.items.length);
    listEl.innerHTML = "";
    data.items.forEach(function (item) {
      var li = document.createElement("li");

      var text = document.createElement("div");
      var strong = document.createElement("strong");
      strong.textContent = item.name;
      text.appendChild(strong);

      var meta = document.createElement("span");
      var bits = [item.code, item.issuer, item.category, item.note].filter(Boolean);
      meta.textContent = bits.join(" · ");
      text.appendChild(meta);

      if (item.file) {
        var link = document.createElement("a");
        link.href = item.file;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "View uploaded file";
        text.appendChild(link);
      }
      li.appendChild(text);

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn btn-outline danger";
      remove.textContent = "Delete";
      remove.addEventListener("click", function () {
        if (!window.confirm("Delete \"" + item.name + "\"? This also removes any uploaded file.")) return;
        api("/api/certifications/" + encodeURIComponent(item.id), { method: "DELETE" })
          .then(load)
          .then(function () { say("Deleted."); })
          .catch(function (error) { say(error.message, true); });
      });
      li.appendChild(remove);

      listEl.appendChild(li);
    });
  }

  function load() {
    return api("/api/certifications").then(function (data) {
      show(disabledCard, !data.adminEnabled);
      show(loginCard, data.adminEnabled && !data.admin);
      show(panel, data.admin === true);
      if (data.admin) render(data);
      return data;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    msgEl = document.getElementById("msg");
    listEl = document.getElementById("list");
    countEl = document.getElementById("count");
    panel = document.getElementById("admin-panel");
    loginCard = document.getElementById("login-card");
    disabledCard = document.getElementById("disabled-card");

    load().catch(function (error) { say(error.message, true); });

    document.getElementById("login-form").addEventListener("submit", function (event) {
      event.preventDefault();
      var password = event.target.password.value;
      api("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: password })
      })
        .then(function () { event.target.reset(); return load(); })
        .then(function () { say("Signed in."); })
        .catch(function (error) { say(error.message, true); });
    });

    document.getElementById("logout").addEventListener("click", function () {
      api("/api/admin/logout", { method: "POST" })
        .then(load)
        .then(function () { say("Signed out."); })
        .catch(function (error) { say(error.message, true); });
    });

    document.getElementById("cert-form").addEventListener("submit", function (event) {
      event.preventDefault();
      var form = event.target;
      var button = form.querySelector("button[type=submit]");
      button.disabled = true;
      api("/api/certifications", { method: "POST", body: new FormData(form) })
        .then(function (body) {
          form.reset();
          say("Added " + body.item.name + ".");
          return load();
        })
        .catch(function (error) { say(error.message, true); })
        .then(function () { button.disabled = false; });
    });
  });
})();
