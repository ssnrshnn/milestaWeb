// Scroll-reveal for cards + current year in the footer.
document.addEventListener("DOMContentLoaded", () => {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.15 }
  );
  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));

  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  initHeroDepth();
  initShowcase();
});

// Landing page hero: the poster and the card drift at different speeds as the
// page scrolls, for a little depth. Nothing moves when reduced motion is on.
function initHeroDepth() {
  const art = document.querySelector(".hero-art");
  if (!art || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let frame = 0;
  const paint = () => {
    frame = 0;
    art.style.setProperty("--py", Math.min(window.scrollY, 900).toFixed(1));
  };
  window.addEventListener("scroll", () => {
    if (!frame) frame = requestAnimationFrame(paint);
  }, { passive: true });
  paint();
}

// Screenshot carousel on the landing page. CSS scroll-snap does the swiping;
// this adds autoplay, the buttons and dots, and the centre emphasis.
// Autoplay waits until the carousel is on screen, pauses on hover, keyboard
// focus, and hidden tabs, stops for good once the visitor takes over, and
// never starts on its own when reduced motion is requested.
function initShowcase() {
  const root = document.querySelector("[data-carousel]");
  if (!root) return;

  const INTERVAL = 5000; // ms per screenshot
  const track = root.querySelector(".carousel-track");
  const slides = Array.from(track.querySelectorAll(".slide"));
  const toggle = root.querySelector(".carousel-toggle");
  const status = root.querySelector("[data-carousel-status]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const count = slides.length;

  let index = 0;
  let playing = !reduceMotion.matches;
  const holds = new Set(["offscreen"]); // reasons autoplay is paused right now
  let timer = 0;
  let dueAt = 0;
  let remaining = INTERVAL;
  let settling = false; // true while the track scrolls because we asked it to
  let settleTimer = 0;

  root.style.setProperty("--interval", INTERVAL + "ms");

  const dots = slides.map((slide, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "carousel-dot";
    dot.setAttribute("aria-controls", track.id);
    dot.setAttribute("aria-label", `Screenshot ${i + 1} of ${count}: ${slide.dataset.title}`);
    dot.addEventListener("click", () => goTo(i, true));
    root.querySelector(".carousel-dots").append(dot);
    slide.addEventListener("click", () => {
      if (i !== index) goTo(i, true);
    });
    return dot;
  });

  // Slide centres in scroll coordinates, measured once per layout width so
  // the scroll handler only has to read scrollLeft.
  let centres = [];
  let halfWidth = 0;
  let pitch = 1;
  function measure() {
    centres = slides.map((slide) => slide.offsetLeft + slide.offsetWidth / 2);
    halfWidth = track.clientWidth / 2;
    pitch = count > 1 ? centres[1] - centres[0] : 1;
  }
  const offsetFor = (i) => centres[i] - halfWidth;

  function nearest() {
    const centre = track.scrollLeft + halfWidth;
    let best = 0;
    centres.forEach((c, i) => {
      if (Math.abs(c - centre) < Math.abs(centres[best] - centre)) best = i;
    });
    return best;
  }

  // Scale and dim each phone by its distance from the centre, so swipes and
  // autoplay both glide instead of jumping between states.
  function paintDepth() {
    const centre = track.scrollLeft + halfWidth;
    slides.forEach((slide, i) => {
      const distance = Math.abs(centres[i] - centre) / pitch;
      slide.style.setProperty("--p", Math.min(distance, 1).toFixed(3));
    });
  }

  function schedule() {
    clearTimeout(timer);
    timer = 0;
    const held = holds.size > 0;
    root.classList.toggle("is-playing", playing);
    root.classList.toggle("is-held", playing && held);
    toggle.setAttribute("aria-label", playing ? "Pause the slideshow" : "Play the slideshow");
    if (!playing || held) return;
    dueAt = performance.now() + remaining;
    timer = setTimeout(() => goTo(index + 1, false), remaining);
  }

  function hold(reason) {
    if (holds.has(reason)) return;
    if (timer) remaining = Math.max(0, dueAt - performance.now());
    holds.add(reason);
    schedule();
  }

  function release(reason) {
    if (holds.delete(reason)) schedule();
  }

  function play() {
    playing = true;
    remaining = INTERVAL;
    schedule();
  }

  function stop() {
    playing = false;
    remaining = INTERVAL;
    schedule();
  }

  function setActive(i, announce) {
    index = i;
    slides.forEach((slide, j) => slide.classList.toggle("is-active", j === i));
    dots.forEach((dot, j) => {
      if (j === i) dot.setAttribute("aria-current", "true");
      else dot.removeAttribute("aria-current");
    });
    if (announce) status.textContent = `Screenshot ${i + 1} of ${count}: ${slides[i].dataset.title}`;
    remaining = INTERVAL;
    schedule();
  }

  function scrollToIndex(i, smooth) {
    const left = offsetFor(i);
    if (Math.abs(track.scrollLeft - left) < 2) {
      settling = false;
      return;
    }
    settling = true;
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => (settling = false), 1500);
    track.scrollTo({ left, behavior: smooth && !reduceMotion.matches ? "smooth" : "auto" });
  }

  function goTo(i, byVisitor) {
    i = (i + count) % count;
    if (byVisitor) stop();
    scrollToIndex(i, true);
    setActive(i, byVisitor);
  }

  let frame = 0;
  track.addEventListener(
    "scroll",
    () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        paintDepth();
        const drift = Math.abs(track.scrollLeft - offsetFor(index));
        if (settling) {
          if (drift < 2) settling = false;
          return;
        }
        if (drift < 2) return;
        // The visitor is swiping or scrolling sideways: hand over control.
        if (playing) stop();
        const i = nearest();
        if (i !== index) setActive(i, true);
      });
    },
    { passive: true }
  );
  track.addEventListener("scrollend", () => (settling = false));
  // A touch that turns into a swipe should win over an autoplay scroll.
  track.addEventListener("pointerdown", () => (settling = false), { passive: true });

  track.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return; // leave browser shortcuts alone
    const target = { ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: count - 1 }[e.key];
    if (target === undefined) return;
    e.preventDefault();
    goTo(target, true);
  });

  root.querySelectorAll("[data-step]").forEach((button) =>
    button.addEventListener("click", () => goTo(index + Number(button.dataset.step), true))
  );
  toggle.addEventListener("click", () => (playing ? stop() : play()));

  track.addEventListener("pointerenter", (e) => {
    if (e.pointerType === "mouse") hold("hover");
  });
  track.addEventListener("pointerleave", () => release("hover"));

  // Keyboard focus pauses; focus on the play/pause button itself does not,
  // so pressing Play starts the slideshow straight away.
  root.addEventListener("focusin", (e) => {
    let keyboard = true;
    try {
      keyboard = e.target.matches(":focus-visible");
    } catch (_) {}
    if (keyboard && e.target !== toggle) hold("focus");
    else release("focus");
  });
  root.addEventListener("focusout", (e) => {
    if (!root.contains(e.relatedTarget)) release("focus");
  });

  document.addEventListener("visibilitychange", () =>
    document.hidden ? hold("hidden") : release("hidden")
  );
  new IntersectionObserver(
    ([entry]) =>
      entry.isIntersecting && entry.intersectionRatio >= 0.4 ? release("offscreen") : hold("offscreen"),
    { threshold: [0, 0.4] }
  ).observe(track);

  if (reduceMotion.addEventListener) {
    reduceMotion.addEventListener("change", () => {
      if (reduceMotion.matches) stop();
    });
  }

  // Keep the current phone centred when the layout width changes.
  new ResizeObserver(() => {
    measure();
    scrollToIndex(index, false);
    paintDepth();
  }).observe(track);

  root.querySelector(".carousel-controls").hidden = false;
  measure();
  paintDepth();
  setActive(0, false);
}
