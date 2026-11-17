/* Small progressive enhancements shared by public and account screens. */
(function () {
  "use strict";

  Array.prototype.forEach.call(document.querySelectorAll("[data-menu]"), function (menu) {
    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) menu.open = false;
    });
    document.addEventListener("click", function (event) {
      if (!menu.contains(event.target)) menu.open = false;
    });
    menu.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menu.open) {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
  });

  var workspaceNav = document.querySelector("[data-workspace-nav]");
  if (workspaceNav) {
    var desktop = window.matchMedia("(min-width: 1040px)");
    var syncNav = function () { workspaceNav.open = desktop.matches; };
    syncNav();
    desktop.addEventListener("change", syncNav);
    workspaceNav.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !desktop.matches && workspaceNav.open) {
        workspaceNav.open = false;
        workspaceNav.querySelector("summary").focus();
      }
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-password-toggle]"), function (button) {
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", (show ? "Hide " : "Show ") + button.dataset.passwordLabel);
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll(".field--error"), function (field) {
    var input = field.querySelector("input, select, textarea");
    var errors = field.querySelector(".field__errors[id]");
    if (!input || !errors) return;
    var ids = (input.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    if (ids.indexOf(errors.id) === -1) ids.push(errors.id);
    input.setAttribute("aria-describedby", ids.join(" "));
    input.setAttribute("aria-invalid", "true");
  });

  Array.prototype.forEach.call(document.querySelectorAll("[data-error-summary] a"), function (link) {
    link.addEventListener("click", function (event) {
      var input = document.getElementById(link.hash.slice(1));
      if (!input) return;
      event.preventDefault();
      var details = input.closest("details");
      if (details) details.open = true;
      input.focus();
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll("[data-dismiss-message]"), function (button) {
    button.hidden = false;
    button.addEventListener("click", function () {
      var flash = button.closest(".flash");
      var next = flash.nextElementSibling;
      flash.remove();
      var target = next && next.querySelector("[data-dismiss-message]");
      if (!target) target = document.querySelector("#main h1, #main h2");
      if (target) {
        if (!target.matches("button")) target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      }
    });
  });
})();
