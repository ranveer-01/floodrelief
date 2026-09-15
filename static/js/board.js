/* ==========================================================================
   board.js — live board behaviour: bring a brand-new request into view,
   then tidy the URL so a refresh doesn't keep re-announcing it.
   ========================================================================== */
(function () {
  "use strict";

  var board = document.querySelector("[data-board]");
  if (!board) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------- the request just filed --- */
  var highlightId = board.getAttribute("data-highlight");
  if (highlightId) {
    var card = document.getElementById("req-" + highlightId);

    if (card) {
      // The card is already marked .is-new server-side; make sure the reveal
      // observer doesn't hold it at opacity 0 before we scroll to it.
      card.classList.add("is-visible");

      window.requestAnimationFrame(function () {
        var top = card.getBoundingClientRect().top + window.scrollY - 140;
        window.scrollTo({ top: Math.max(top, 0), behavior: reduced ? "auto" : "smooth" });
      });

      // Drop ?highlight= so a reload shows the board in its normal state.
      if (window.history && window.history.replaceState) {
        window.setTimeout(function () {
          var url = new URL(window.location.href);
          url.searchParams.delete("highlight");
          window.history.replaceState({}, "", url.pathname + url.search + "#req-" + highlightId);
        }, 2500);
      }
    }
  }

  /* ------------------------------------------------------ filter form --- */
  var filterForm = document.querySelector("[data-filter-form]");
  if (filterForm) {
    Array.prototype.forEach.call(
      filterForm.querySelectorAll("[data-autosubmit]"),
      function (control) {
        control.addEventListener("change", function () {
          filterForm.submit();
        });
      }
    );
  }
})();
