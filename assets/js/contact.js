// Contact form: posts to /api/messages and reports the outcome inline.
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("contact-form");
    if (!form) return;

    var msg = document.getElementById("contact-msg");
    var button = form.querySelector("button[type=submit]");

    function say(text, kind) {
      msg.textContent = text;
      msg.className = "form-msg" + (kind ? " " + kind : "");
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var payload = {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        subject: form.subject.value.trim(),
        message: form.message.value.trim(),
        website: form.website.value
      };

      if (!payload.name || !payload.email || !payload.message) {
        say("Please fill in your name, email and message.", "error");
        return;
      }

      button.disabled = true;
      say("Sending...");

      fetch("/api/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (body) {
            if (!response.ok) throw new Error(body.error || "Something went wrong. Please email me instead.");
            return body;
          });
        })
        .then(function () {
          form.reset();
          say("Thank you - your message reached me. I will reply within 24 hours.", "ok");
        })
        .catch(function (error) { say(error.message, "error"); })
        .then(function () { button.disabled = false; });
    });
  });
})();
