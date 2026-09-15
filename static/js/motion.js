/* ==========================================================================
   motion.js — scroll reveals, sticky masthead, counters, lifecycle animation,
   and live relative timestamps. Loaded on every page.

   Rules of the road:
   - transform/opacity only, so low-end devices don't repaint layout
   - every observer unhooks itself after firing once
   - if the user prefers reduced motion, everything lands in its final state
   ========================================================================== */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var supportsIO = "IntersectionObserver" in window;

  /* ---------------------------------------------------------- reveals --- */
  function reveal(el) {
    el.classList.add("is-visible");
  }

  var revealables = document.querySelectorAll("[data-reveal]");

  if (reduced || !supportsIO) {
    Array.prototype.forEach.call(revealables, reveal);
  } else {
    var revealObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        reveal(entry.target);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.08 });

    Array.prototype.forEach.call(revealables, function (el) {
      revealObserver.observe(el);
    });
  }

  /* -------------------------------------------------- one-shot triggers --- */
  /* Adds `className` to each match the first time it scrolls into view. */
  function onceInView(selector, className, threshold) {
    var nodes = document.querySelectorAll(selector);
    if (!nodes.length) return;

    if (reduced || !supportsIO) {
      Array.prototype.forEach.call(nodes, function (el) {
        el.classList.add(className);
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add(className);
        obs.unobserve(entry.target);
      });
    }, { threshold: threshold || 0.25 });

    Array.prototype.forEach.call(nodes, function (el) {
      observer.observe(el);
    });
  }

  // Status tracker fill (Received -> Closed), lifecycle rail, duplicate stack.
  onceInView("[data-tracker]", "is-live", 0.35);
  onceInView("[data-rail]", "is-live", 0.2);
  onceInView("[data-collapse]", "is-collapsed", 0.45);

  /* -------------------------------------------------------- masthead ----- */
  var masthead = document.querySelector("[data-masthead]");
  if (masthead) {
    var stuck = false;
    var ticking = false;

    var syncMasthead = function () {
      var shouldStick = window.scrollY > 24;
      if (shouldStick !== stuck) {
        stuck = shouldStick;
        masthead.classList.toggle("is-stuck", stuck);
      }
      ticking = false;
    };

    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(syncMasthead);
    }, { passive: true });

    syncMasthead();
  }

  /* -------------------------------------------------------- counters ----- */
  /* Counts an integer up over ~380ms. Skipped entirely under reduced motion. */
  function countUp(el) {
    var target = parseInt(el.getAttribute("data-count"), 10);
    if (isNaN(target) || target === 0) return;

    var duration = 380;
    var start = null;

    function step(timestamp) {
      if (start === null) start = timestamp;
      var progress = Math.min((timestamp - start) / duration, 1);
      // ease-out so it decelerates into the real number
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = String(Math.round(target * eased));
      if (progress < 1) window.requestAnimationFrame(step);
      else el.textContent = String(target);
    }

    window.requestAnimationFrame(step);
  }

  var counters = document.querySelectorAll("[data-count]");
  if (counters.length && !reduced && supportsIO) {
    var counterObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        countUp(entry.target);
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.5 });

    Array.prototype.forEach.call(counters, function (el) {
      counterObserver.observe(el);
    });
  }

  /* ----------------------------------------------- relative timestamps --- */
  /* The exact timestamp stays on screen — the relative part is appended, so
     "18 Sep 2026 · 14:32:11" becomes "18 Sep 2026 · 14:32:11 4 min ago". */
  function relativeFrom(iso) {
    var then = new Date(iso).getTime();
    if (isNaN(then)) return "";

    var seconds = Math.round((Date.now() - then) / 1000);
    if (seconds < 0) return "just now";
    if (seconds < 45) return "just now";
    if (seconds < 90) return "1 min ago";

    var minutes = Math.round(seconds / 60);
    if (minutes < 60) return minutes + " min ago";

    var hours = Math.floor(minutes / 60);
    if (hours < 24) {
      var rem = minutes % 60;
      return rem ? hours + "h " + rem + "m ago" : hours + "h ago";
    }

    var days = Math.floor(hours / 24);
    if (days < 7) return days + "d " + (hours % 24) + "h ago";
    return days + "d ago";
  }

  function syncTimes() {
    var stamps = document.querySelectorAll("time[data-relative]");
    Array.prototype.forEach.call(stamps, function (el) {
      var iso = el.getAttribute("datetime");
      if (!iso) return;

      if (!el.dataset.absolute) {
        el.dataset.absolute = el.textContent.trim();
        el.setAttribute("title", new Date(iso).toString());
      }

      var rel = relativeFrom(iso);
      var suffix = el.querySelector(".time-rel");

      if (!suffix) {
        el.textContent = el.dataset.absolute + " ";
        suffix = document.createElement("span");
        suffix.className = "time-rel";
        el.appendChild(suffix);
      }
      suffix.textContent = rel;
    });
  }

  syncTimes();
  window.setInterval(syncTimes, 30000);
})();
