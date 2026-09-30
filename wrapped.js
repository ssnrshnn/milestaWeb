/* Milesta landing page — the "Wrapped" design. No dependencies. */
(function () {
  "use strict";

  var root = document.documentElement;
  var isStatic = root.classList.contains("static");
  var reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  var hasIO = "IntersectionObserver" in window;
  function motionAllowed() { return !isStatic && !reduceQuery.matches; }

  /* ---------- Pause / play decorative motion ---------- */
  var toggles = Array.prototype.slice.call(document.querySelectorAll("[data-motion-toggle]"));
  function setPaused(paused, remember) {
    root.classList.toggle("motion-paused", paused);
    toggles.forEach(function (b) {
      b.setAttribute("aria-pressed", String(paused));
    });
    if (remember) {
      try { localStorage.setItem("milesta-wrapped-paused", paused ? "1" : "0"); } catch (e) {}
    }
  }
  toggles.forEach(function (b) {
    b.addEventListener("click", function () { setPaused(!root.classList.contains("motion-paused"), true); });
  });
  try { if (localStorage.getItem("milesta-wrapped-paused") === "1") setPaused(true, false); } catch (e) {}

  /* Pause infinite animations while they are off screen. */
  if (hasIO) {
    var offscreen = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.target.classList.toggle("is-offscreen", !e.isIntersecting); });
    });
    document.querySelectorAll(".top-bg, .hero, .tapes, .finale").forEach(function (el) { offscreen.observe(el); });
  }

  /* ---------- Scroll reveal ---------- */
  var reveals = document.querySelectorAll("[data-reveal]");
  if (!motionAllowed() || !hasIO) {
    reveals.forEach(function (el) { el.classList.add("in"); });
  } else {
    var revealIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); revealIO.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    reveals.forEach(function (el) { revealIO.observe(el); });
  }

  /* ---------- Count-up numbers (the final value is in the HTML) ---------- */
  var counters = document.querySelectorAll("[data-count]");
  if (motionAllowed() && hasIO) {
    counters.forEach(function (el) { el.textContent = "0"; });
    var countIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        countIO.unobserve(e.target);
        countUp(e.target);
      });
    }, { threshold: 0.55 });
    counters.forEach(function (el) { countIO.observe(el); });
  }
  function countUp(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    var duration = 1500 + target * 10;
    var start = null;
    function easeOutExpo(t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); }
    function frame(now) {
      if (start === null) start = now;
      var p = Math.min(1, (now - start) / duration);
      el.textContent = String(Math.round(target * easeOutExpo(p)));
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* ---------- Poster style tabs ---------- */
  var section = document.getElementById("posters");
  var panel = document.getElementById("poster-panel");
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".style-tab"));
  var galleryImg = document.getElementById("poster-gallery-img");
  var pathImg = document.getElementById("poster-path-img");
  var STYLES = {
    aurora: {
      g: "assets/wrapped/poster-yearA-2025-aurora.webp", p: "assets/wrapped/poster-yearB-2025-aurora.webp",
      ga: "Year poster, Gallery layout, Aurora style: 2025, 51 milestones and 13 places, with photos of the biggest moments and the year at a glance.",
      pa: "Year poster, Path layout, Aurora style: 2025’s 51 milestones along a winding path, with photo stops for the biggest moments."
    },
    sunset: {
      g: "assets/wrapped/poster-yearA-2023-sunset.webp", p: "assets/wrapped/poster-yearB-2023-sunset.webp",
      ga: "Year poster, Gallery layout, Sunset style: 2023, 12 milestones and 2 places, shown with icons because that year has no photos.",
      pa: "Year poster, Path layout, Sunset style: 2023’s 12 milestones along a winding path."
    },
    noir: {
      g: "assets/wrapped/poster-yearA-2025-noir.webp", p: "assets/wrapped/poster-yearB-2025-noir.webp",
      ga: "Year poster, Gallery layout, Noir style: 2025, 51 milestones and 13 places, in black and white with full-colour photos.",
      pa: "Year poster, Path layout, Noir style: 2025’s 51 milestones as white dots along a dark, winding path."
    },
    linen: {
      g: "assets/wrapped/poster-yearA-2025-linen.webp", p: "assets/wrapped/poster-yearB-2025-linen.webp",
      ga: "Year poster, Gallery layout, Linen style: 2025, 51 milestones and 13 places, on light paper.",
      pa: "Year poster, Path layout, Linen style: 2025’s 51 milestones along a winding path on light paper."
    },
    classic: {
      g: "assets/wrapped/poster-yearA-2025-classic.webp", p: "assets/wrapped/poster-yearB-2025-classic.webp",
      ga: "Year poster, Gallery layout, Classic style: 2025, 51 milestones and 13 places, in warm terracotta.",
      pa: "Year poster, Path layout, Classic style: 2025’s 51 milestones along a winding path in warm terracotta."
    }
  };
  var preloaded = {};
  function preload(key) {
    if (preloaded[key] || !STYLES[key]) return;
    preloaded[key] = true;
    [STYLES[key].g, STYLES[key].p].forEach(function (src) { var i = new Image(); i.decoding = "async"; i.src = src; });
  }
  function swap(img, src, alt) {
    if (!img || img.getAttribute("src") === src) return;
    var fig = img.closest(".poster");
    var next = new Image();
    next.src = src;
    var wait = motionAllowed() ? 260 : 0;
    if (wait) fig.classList.add("is-swapping");
    var ready = next.decode ? next.decode().catch(function () {}) : Promise.resolve();
    var timer = new Promise(function (r) { setTimeout(r, wait); });
    Promise.all([ready, timer]).then(function () {
      img.src = src;
      img.alt = alt;
      requestAnimationFrame(function () { fig.classList.remove("is-swapping"); });
    });
  }
  function select(tab, moveFocus) {
    var key = tab.getAttribute("data-style");
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    if (moveFocus) tab.focus();
    section.setAttribute("data-style", key);
    panel.setAttribute("aria-labelledby", tab.id);
    swap(galleryImg, STYLES[key].g, STYLES[key].ga);
    swap(pathImg, STYLES[key].p, STYLES[key].pa);
  }
  tabs.forEach(function (tab, i) {
    tab.addEventListener("click", function () { select(tab, false); });
    tab.addEventListener("pointerenter", function () { preload(tab.getAttribute("data-style")); });
    tab.addEventListener("focus", function () { preload(tab.getAttribute("data-style")); });
    tab.addEventListener("keydown", function (e) {
      var j = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % tabs.length;
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = tabs.length - 1;
      if (j !== null) { e.preventDefault(); select(tabs[j], true); }
    });
  });

  /* ---------- Pointer parallax on the poster drum, and bento spotlights ---------- */
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (finePointer && motionAllowed()) {
    var hero = document.querySelector(".hero");
    var tilt = document.querySelector(".drum-tilt");
    if (hero && tilt) {
      var raf = 0;
      hero.addEventListener("pointermove", function (e) {
        if (raf) return;
        raf = requestAnimationFrame(function () {
          raf = 0;
          var r = hero.getBoundingClientRect();
          var x = (e.clientX - r.left) / r.width - 0.5;
          var y = (e.clientY - r.top) / r.height - 0.5;
          tilt.style.setProperty("--px", (x * 9).toFixed(2) + "deg");
          tilt.style.setProperty("--py", (-y * 5).toFixed(2) + "deg");
        });
      });
      hero.addEventListener("pointerleave", function () {
        tilt.style.setProperty("--px", "0deg");
        tilt.style.setProperty("--py", "0deg");
      });
    }
  }
  if (finePointer) {
    document.querySelectorAll(".tile").forEach(function (t) {
      t.addEventListener("pointermove", function (e) {
        var r = t.getBoundingClientRect();
        t.style.setProperty("--mx", (e.clientX - r.left) + "px");
        t.style.setProperty("--my", (e.clientY - r.top) + "px");
      });
    });
  }

  /* ---------- Sideways rails (month cards, the everyday island on phones) ----------
     Images inside a rail are clipped by it, so lazy loading alone would wait
     for a swipe: load them once the rail comes near. A rail is a tab stop
     only while it actually scrolls. */
  var rails = Array.prototype.slice.call(document.querySelectorAll("[data-eager-near]"));
  function loadRail(rail) {
    rail.querySelectorAll("img[loading='lazy']").forEach(function (img) { img.loading = "eager"; });
  }
  if (hasIO) {
    var railIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { loadRail(e.target); railIO.unobserve(e.target); }
      });
    }, { rootMargin: "600px 0px" });
    rails.forEach(function (r) { railIO.observe(r); });
  } else {
    rails.forEach(loadRail);
  }
  function railFocus() {
    rails.forEach(function (rail) {
      if (rail.scrollWidth > rail.clientWidth + 2) rail.setAttribute("tabindex", "0");
      else rail.removeAttribute("tabindex");
    });
  }
  railFocus();
  window.addEventListener("resize", railFocus, { passive: true });

  /* ---------- Footer year ---------- */
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = String(new Date().getFullYear());
})();
