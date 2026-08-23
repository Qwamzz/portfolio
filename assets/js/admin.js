// Site admin: schema-driven editing for every content collection.
(function () {
  "use strict";

  var schema = {};
  var current = null;      // collection key
  var editing = null;      // item being edited, or null for a new one
  var nodes = {};

  function say(text, isError) {
    nodes.msg.textContent = text || "";
    nodes.msg.className = "admin-msg" + (text ? (isError ? " error" : " ok") : "");
    if (text && !isError) {
      setTimeout(function () { if (nodes.msg.textContent === text) say(""); }, 4000);
    }
  }

  function api(url, options) {
    return fetch(url, Object.assign({ credentials: "same-origin" }, options || {}))
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          if (!response.ok) throw new Error(body.error || ("Request failed (" + response.status + ")"));
          return body;
        });
      });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  // ---------- Navigation ----------
  function buildNav() {
    var nav = document.getElementById("collection-nav");
    nav.innerHTML = "";

    var pages = [];
    Object.keys(schema).forEach(function (key) {
      var page = schema[key].page;
      if (pages.indexOf(page) === -1) pages.push(page);
    });

    pages.forEach(function (page) {
      nav.appendChild(el("span", "admin-side-label", page));
      Object.keys(schema).forEach(function (key) {
        if (schema[key].page !== page) return;
        var button = el("button", "admin-side-link", schema[key].label);
        button.type = "button";
        button.dataset.key = key;
        if (key === current) button.classList.add("active");
        button.addEventListener("click", function () { select(key); });
        nav.appendChild(button);
      });
    });
  }

  function select(key) {
    current = key;
    editing = null;
    nodes.editor.hidden = true;
    buildNav();
    document.getElementById("collection-title").textContent = schema[key].label;
    document.getElementById("collection-hint").textContent = schema[key].single
      ? "This section holds a single entry."
      : "Entries appear on the site in the order listed here.";
    return loadItems();
  }

  // ---------- Item list ----------
  function summarise(item) {
    var spec = schema[current];
    var bits = [];
    spec.fields.forEach(function (field) {
      if (field.name === spec.title_field || field.type === "file") return;
      var value = item[field.name];
      if (Array.isArray(value)) {
        if (value.length) bits.push(value.length + " " + (value.length === 1 ? "line" : "lines"));
      } else if (value) {
        bits.push(String(value).slice(0, 60));
      }
    });
    return bits.slice(0, 3).join(" · ");
  }

  function loadItems() {
    return api("/api/content/" + current).then(function (data) {
      var spec = schema[current];
      var list = document.getElementById("list");
      list.innerHTML = "";

      document.getElementById("add-new").hidden = !!(spec.single && data.items.length);

      if (!data.items.length) {
        list.appendChild(el("li", null, "Nothing here yet."));
        return data;
      }

      data.items.forEach(function (item, index) {
        var li = el("li");

        var text = el("div");
        text.appendChild(el("strong", null, item[spec.title_field] || "(untitled)"));
        var summary = summarise(item);
        if (summary) text.appendChild(el("span", null, summary));
        if (item.file) {
          var fileLink = el("a", null, "View uploaded file");
          fileLink.href = item.file;
          fileLink.target = "_blank";
          fileLink.rel = "noopener";
          text.appendChild(fileLink);
        }
        li.appendChild(text);

        if (!spec.single) {
          li.appendChild(moveButton(item, "up", "↑", index === 0));
          li.appendChild(moveButton(item, "down", "↓", index === data.items.length - 1));
        }

        var edit = el("button", "btn btn-outline", "Edit");
        edit.type = "button";
        edit.addEventListener("click", function () { openEditor(item); });
        li.appendChild(edit);

        var remove = el("button", "btn btn-outline danger", "Delete");
        remove.type = "button";
        remove.addEventListener("click", function () {
          var name = item[spec.title_field] || "this entry";
          if (!window.confirm("Delete \"" + name + "\"?")) return;
          api("/api/content/" + current + "/" + encodeURIComponent(item.id), { method: "DELETE" })
            .then(function () { nodes.editor.hidden = true; return loadItems(); })
            .then(function () { say("Deleted."); })
            .catch(function (error) { say(error.message, true); });
        });
        li.appendChild(remove);

        list.appendChild(li);
      });

      return data;
    });
  }

  function moveButton(item, direction, glyph, disabled) {
    var button = el("button", "btn btn-outline move", glyph);
    button.type = "button";
    button.disabled = disabled;
    button.title = direction === "up" ? "Move up" : "Move down";
    button.addEventListener("click", function () {
      api("/api/content/" + current + "/" + encodeURIComponent(item.id) + "/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ direction: direction })
      }).then(loadItems).catch(function (error) { say(error.message, true); });
    });
    return button;
  }

  // ---------- Editor ----------
  function fieldControl(field, value) {
    var control;
    if (field.type === "textarea") {
      control = document.createElement("textarea");
      control.rows = 5;
      control.value = value || "";
    } else if (field.type === "lines") {
      control = document.createElement("textarea");
      control.rows = 5;
      control.value = (value || []).join("\n");
    } else if (field.type === "select") {
      control = document.createElement("select");
      (field.options || []).forEach(function (option) {
        var node = document.createElement("option");
        node.value = node.textContent = option;
        if (option === value) node.selected = true;
        control.appendChild(node);
      });
    } else if (field.type === "file") {
      control = document.createElement("input");
      control.type = "file";
      control.accept = ".png,.jpg,.jpeg,.webp,.gif,.pdf";
    } else {
      control = document.createElement("input");
      control.type = "text";
      control.value = value || "";
    }
    control.name = field.name;
    if (field.required && field.type !== "file") control.required = true;
    return control;
  }

  function openEditor(item) {
    var spec = schema[current];
    editing = item || null;

    document.getElementById("editor-title").textContent =
      item ? "Edit: " + (item[spec.title_field] || "entry") : "New entry";

    var form = document.getElementById("item-form");
    form.innerHTML = "";

    var grid = el("div", "admin-grid");
    var wide = document.createDocumentFragment();

    spec.fields.forEach(function (field) {
      var label = el("label", null, field.label);
      var control = fieldControl(field, item ? item[field.name] : undefined);
      label.appendChild(control);

      if (field.type === "textarea" || field.type === "lines" || field.type === "file") {
        if (field.type === "file" && item && item.file) {
          var current_file = el("span", "admin-hint", "Currently: " + item.file + " (choose a file to replace it)");
          label.appendChild(current_file);
        }
        wide.appendChild(label);
      } else {
        grid.appendChild(label);
      }
    });

    if (grid.childNodes.length) form.appendChild(grid);
    form.appendChild(wide);

    var save = el("button", "btn", item ? "Save changes" : "Add entry");
    save.type = "submit";
    form.appendChild(save);

    nodes.editor.hidden = false;
    nodes.editor.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function submitEditor(event) {
    event.preventDefault();
    var form = event.target;
    var save = form.querySelector("button[type=submit]");
    save.disabled = true;

    var url = "/api/content/" + current + (editing ? "/" + encodeURIComponent(editing.id) : "");
    api(url, { method: "POST", body: new FormData(form) })
      .then(function () {
        nodes.editor.hidden = true;
        editing = null;
        return loadItems();
      })
      .then(function () { say("Saved. The site is updated."); })
      .catch(function (error) { say(error.message, true); })
      .then(function () { save.disabled = false; });
  }

  // ---------- Session ----------
  function load() {
    return api("/api/schema").then(function (data) {
      schema = data.schema;
      nodes.disabled.hidden = data.adminEnabled;
      nodes.login.hidden = !data.adminEnabled || data.admin;
      nodes.panel.hidden = data.admin !== true;
      if (!data.admin) return data;
      return select(current || Object.keys(schema)[0]).then(function () { return data; });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    nodes.msg = document.getElementById("msg");
    nodes.panel = document.getElementById("admin-panel");
    nodes.login = document.getElementById("login-card");
    nodes.disabled = document.getElementById("disabled-card");
    nodes.editor = document.getElementById("editor-card");

    load().catch(function (error) { say(error.message, true); });

    document.getElementById("login-form").addEventListener("submit", function (event) {
      event.preventDefault();
      api("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: event.target.password.value })
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

    document.getElementById("add-new").addEventListener("click", function () { openEditor(null); });
    document.getElementById("cancel-edit").addEventListener("click", function () {
      nodes.editor.hidden = true;
      editing = null;
    });
    document.getElementById("item-form").addEventListener("submit", submitEditor);
  });
})();
