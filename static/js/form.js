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
    textarea.insertAdjacentElement("afterend", counter);

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
  /* Clears the server-rendered error state as soon as the user fixes a field. */
  Array.prototype.forEach.call(form.querySelectorAll(".field__input"), function (input) {
    input.addEventListener("input", function () {
      var field = input.closest(".field");
      if (field && field.classList.contains("field--error") && input.value.trim()) {
        field.classList.remove("field--error");
      }
    });
  });

  function firstEmptyRequired() {
    var inputs = form.querySelectorAll("[aria-required='true']");
    for (var i = 0; i < inputs.length; i++) {
      if (!inputs[i].value.trim()) return inputs[i];
    }
    if (textarea && textarea.value.trim().length < MIN_DESCRIPTION) return textarea;
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
      if (field) field.classList.add("field--error");
      offender.focus({ preventScroll: false });
      if (statusLine) {
        statusLine.textContent = offender === textarea
          ? "Add a little more detail before sending."
          : "One field still needs filling in.";
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
})();
