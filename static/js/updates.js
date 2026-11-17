/* Report fresh workflow activity without replacing a form the user is editing. */
(function () {
  "use strict";
  var notice = document.querySelector("[data-status-watch]");
  if (!notice || !window.fetch || !window.AbortController) return;
  var revision = notice.getAttribute("data-revision");
  var url = notice.getAttribute("data-update-url");
  var stopped = false;
  var timer;
  notice.querySelector("[data-update-refresh]").addEventListener("click", function () { window.location.reload(); });

  function schedule() {
    if (!stopped) timer = window.setTimeout(check, 30000);
  }
  function check() {
    if (document.hidden) { schedule(); return; }
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 8000);
    fetch(url, { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(function (response) {
        if (!response.ok) throw new Error("Updates unavailable");
        return response.json();
      })
      .then(function (snapshot) {
        if (snapshot.revision !== revision) {
          notice.querySelector("[data-update-message]").textContent = snapshot.label
            ? "Current status: " + snapshot.label + ". The record has changed; refresh for the latest details."
            : "New relief activity is available. Refresh to see the latest board.";
          notice.hidden = false;
          stopped = true;
        }
      })
      .catch(function () { /* The normal page and forms remain usable offline. */ })
      .finally(function () { window.clearTimeout(timeout); schedule(); });
  }
  window.addEventListener("pagehide", function () { stopped = true; window.clearTimeout(timer); });
  schedule();
})();
