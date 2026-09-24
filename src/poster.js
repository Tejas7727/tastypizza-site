/* Tasty Pizza — poster direction motion.

   Three things happen, all driven by scroll, none of them a video:

   1. THE PRESS RUN. A drawing's ink plates arrive off-register and slide home,
      staggered, the first time it enters the viewport.
   2. THE DRIFT. Once printed, scroll position nudges the plates a few pixels out
      of true again, at different rates per plate. Parallax, but motivated —
      it is the press losing registration.
   3. THE PALETTE. The page's four ink variables interpolate between sections, so
      the whole site changes colour continuously as you move down it.

   Everything is transform and opacity, so it stays on the compositor. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------ colour */
  function parseHex(h) {
    h = (h || '').trim().replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function mix(a, b, t) {
    return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * t) + ',' +
      Math.round(a[1] + (b[1] - a[1]) * t) + ',' +
      Math.round(a[2] + (b[2] - a[2]) * t) + ')';
  }
  var KEYS = ['paper', 'ink', 'accent', 'pop'];

  function readPalette(el) {
    var cs = getComputedStyle(el), out = {};
    KEYS.forEach(function (k) { out[k] = parseHex(cs.getPropertyValue('--' + k)); });
    return out;
  }

  /* ------------------------------------------------------------ the press run */
  var presses = $$('.press');
  var rails = $$('.rail');

  function printNow(el) {
    el.classList.add('is-printed');
  }

  if (calm) {
    presses.forEach(printNow);
    rails.forEach(function (r) { r.classList.add('is-printed-rail'); });
  } else if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        printNow(en.target);
        io.unobserve(en.target);
      });
    }, { threshold: 0.22, rootMargin: '0px 0px -8% 0px' });
    presses.forEach(function (p) { io.observe(p); });

    var railIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('is-printed-rail');
        railIO.unobserve(en.target);
      });
    }, { threshold: 0.3 });
    rails.forEach(function (r) { railIO.observe(r); });
  } else {
    presses.forEach(printNow);
    rails.forEach(function (r) { r.classList.add('is-printed-rail'); });
  }

  /* ------------------------------------------------------------ drift + palette */
  var sections = $$('[data-palette]').map(function (el) {
    return { el: el, pal: readPalette(el) };
  });
  var root = document.documentElement;
  var ticking = false;

  // how far each plate wanders once it has printed, in px per unit of progress
  var DRIFT = { 1: -16, 2: 11, 3: -7 };

  function frame() {
    ticking = false;
    var vh = window.innerHeight;

    // 1. drift: plates ease out of register as their section leaves the middle
    for (var i = 0; i < presses.length; i++) {
      var p = presses[i];
      if (!p.classList.contains('is-printed')) continue;
      var r = p.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) continue;
      // -1 above the fold, 0 dead centre, +1 below
      var t = ((r.top + r.height / 2) - vh / 2) / vh;
      t = Math.max(-1, Math.min(1, t));
      var plates = p.querySelectorAll('.plate');
      for (var j = 0; j < plates.length; j++) {
        var n = plates[j].getAttribute('data-plate');
        var d = DRIFT[n] || 0;
        plates[j].style.setProperty('--ox', (t * d).toFixed(2) + 'px');
        plates[j].style.setProperty('--oy', (t * d * 0.55).toFixed(2) + 'px');
        plates[j].style.setProperty('--orot', (t * d * 0.05).toFixed(3) + 'deg');
      }
    }

    // 2. palette: find the two sections straddling the viewport middle and blend
    if (sections.length) {
      var mid = vh * 0.42, cur = sections[0], next = null, tt = 0;
      for (var k = 0; k < sections.length; k++) {
        var box = sections[k].el.getBoundingClientRect();
        if (box.top <= mid) { cur = sections[k]; next = sections[k + 1] || null; }
      }
      if (next) {
        var b = next.el.getBoundingClientRect();
        // blend across the last 55% of a viewport before the next section lands
        var span = vh * 0.55;
        tt = 1 - Math.max(0, Math.min(1, (b.top - mid) / span));
      }
      var from = cur.pal, to = next ? next.pal : cur.pal;
      for (var m = 0; m < KEYS.length; m++) {
        root.style.setProperty('--' + KEYS[m], mix(from[KEYS[m]], to[KEYS[m]], tt));
      }
    }
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(frame);
  }

  if (!calm) {
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    // sections own their own vars for the observer to read; the blended result
    // lives on :root and each section opts out of its own so it inherits
    sections.forEach(function (s) {
      KEYS.forEach(function (k) { s.el.style.setProperty('--' + k, 'inherit'); });
    });
    frame();
  }
})();
