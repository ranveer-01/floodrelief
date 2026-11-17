/* ==========================================================================
   form.js — submission page interactions.
   Client-side checks are a courtesy only; Django's ModelForm remains the
   authority on what is valid.
   ========================================================================== */
(function () {
  "use strict";

  var form = document.querySelector("[data-reqform]");
  if (!form) return;

  var button = form.querySelector("[data-submit]");
  var statusLine = form.querySelector("[data-form-status]");
  var MIN_DESCRIPTION = 15;

  /* ------------------------------------------------- character counter --- */
  var textarea = form.querySelector("textarea[data-counter]");
  if (textarea) {
    var max = parseInt(textarea.getAttribute("maxlength"), 10) || 1200;
    var counter = document.createElement("p");
    counter.className = "field__counter mono";
    counter.id = textarea.id + "_counter";
    textarea.closest(".field").appendChild(counter);
    textarea.setAttribute("aria-describedby", ((textarea.getAttribute("aria-describedby") || "") + " " + counter.id).trim());

    var syncCounter = function () {
      var length = textarea.value.trim().length;
      counter.classList.toggle("is-short", length > 0 && length < MIN_DESCRIPTION);
      counter.classList.toggle("is-close", length > max - 120);

      if (length === 0) {
        counter.textContent = max + " characters available";
      } else if (length < MIN_DESCRIPTION) {
        counter.textContent = (MIN_DESCRIPTION - length) + " more characters needed";
      } else {
        counter.textContent = length + " / " + max;
      }
    };

    textarea.addEventListener("input", syncCounter);
    syncCounter();
  }

  /* ------------------------------------------------- per-field feedback -- */
  /* Clear courtesy feedback as input changes; keep server errors until review. */
  Array.prototype.forEach.call(form.querySelectorAll(".field__input, .segmented__input"), function (input) {
    input.addEventListener("input", function () {
      var field = input.closest(".field");
      if (!field) return;
      var error = field.querySelector("[data-client-error]");
      if (!error) return;
      var errorId = error.id;
      error.remove();
      input.setAttribute("aria-describedby", (input.getAttribute("aria-describedby") || "").split(/\s+/).filter(function (id) { return id && id !== errorId; }).join(" "));
      if (!field.querySelector(".field__errors")) {
        field.classList.remove("field--error");
        input.removeAttribute("aria-invalid");
      }
    });
  });

  function firstEmptyRequired() {
    var inputs = form.querySelectorAll("[aria-required='true']");
    for (var i = 0; i < inputs.length; i++) {
      if (!inputs[i].value.trim() || !inputs[i].validity.valid) return inputs[i];
    }
    if (textarea && textarea.value.trim().length < MIN_DESCRIPTION) return textarea;
    var urgency = form.querySelector("input[name='urgency']");
    if (urgency && !form.querySelector("input[name='urgency']:checked")) return urgency;
    return null;
  }

  /* -------------------------------------------------------- submission --- */
  var submitted = false;

  form.addEventListener("submit", function (event) {
    if (submitted) {
      event.preventDefault();
      return;
    }

    var offender = firstEmptyRequired();
    if (offender) {
      event.preventDefault();
      var field = offender.closest(".field");
      var message = offender === textarea ? "Add at least " + MIN_DESCRIPTION + " characters about the situation." : offender.type === "radio" ? "Choose how urgent this request is." : offender.validationMessage || "Please fill in this field.";
      if (field) {
        field.classList.add("field--error");
        var error = field.querySelector("[data-client-error]");
        if (!error) {
          error = document.createElement("p");
          error.className = "field__error";
          error.id = offender.id + "_client_error";
          error.setAttribute("data-client-error", "");
          error.setAttribute("role", "alert");
          field.appendChild(error);
          offender.setAttribute("aria-describedby", ((offender.getAttribute("aria-describedby") || "") + " " + error.id).trim());
        }
        error.textContent = message;
        offender.setAttribute("aria-invalid", "true");
      }
      var details = offender.closest("details");
      if (details) details.open = true;
      offender.focus({ preventScroll: false });
      if (statusLine) {
        statusLine.textContent = offender === textarea
          ? "Add a little more detail before sending."
          : "Please check the highlighted field.";
      }
      return;
    }

    // Let the real POST happen — this only dresses the wait.
    submitted = true;

    if (button) {
      var label = button.querySelector(".btn__label");
      button.classList.add("is-sending");
      button.setAttribute("aria-busy", "true");
      if (label) label.textContent = "Logging your request…";
    }

    if (statusLine) {
      var now = new Date();
      var stamp = String(now.getHours()).padStart(2, "0") + ":" +
                  String(now.getMinutes()).padStart(2, "0") + ":" +
                  String(now.getSeconds()).padStart(2, "0");
      statusLine.textContent = "Sent at " + stamp + " — writing it to the board…";
    }
  });

  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    submitted = false;
    if (button) {
      button.classList.remove("is-sending");
      button.removeAttribute("aria-busy");
      button.querySelector(".btn__label").textContent = "Send this request";
    }
    if (statusLine) statusLine.textContent = "";
  });
})();
