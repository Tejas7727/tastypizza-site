/* Tasty Pizza — brand direction motion.

   Deliberately small. The reveals and the turntable are CSS scroll-driven
   animations (animation-timeline), which run on the compositor with no
   library and no scroll listener at all. This file only does the two things
   CSS cannot:

     1. smooth wheel, via Lenis — 3KB, and the single biggest change to how a
        site feels under the hand. Every site with good scroll uses it.
     2. a fallback reveal for browsers without scroll-driven animations
        (~16% in 2026), using IntersectionObserver.

   No GSAP. A 60KB animation engine to fade some cards in would be indefensible
   on a takeaway site where half the traffic is on a phone on mobile data. */
(function () {
  'use strict';

  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------ smooth wheel */
  if (!calm && typeof Lenis !== 'undefined') {
    var lenis = new Lenis({
      lerp: 0.085,          // lower = more glide; 0.085 is smooth without feeling laggy
      wheelMultiplier: 0.95,
      anchors: true,        // in-page links stay smooth
      autoRaf: true,
      autoToggle: true      // steps aside for nested scrollers and modals
    });
    window.__lenis = lenis;
  }

  /* ------------------------------------------------------------ reveal fallback */
  var hasTimeline = CSS && CSS.supports && CSS.supports('animation-timeline', 'view()');
  if (!hasTimeline && !calm && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('in');
        io.unobserve(en.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    $$('[data-anim],[data-stagger]').forEach(function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------------ the turntable
     scroll(root) is not supported everywhere either. Where it is missing, drive
     the same rotation from the one rAF Lenis is already running. */
  if (!calm && !CSS.supports('animation-timeline', 'scroll(root)')) {
    var spin = $$('.disc-spin').concat($$('.orbit'));
    if (spin.length) {
      var tick = function () {
        var max = document.documentElement.scrollHeight - window.innerHeight;
        var p = max > 0 ? window.scrollY / max : 0;
        spin.forEach(function (el) {
          var deg = el.classList.contains('orbit') ? -34 : 58;
          el.style.transform = 'rotate(' + (p * deg).toFixed(2) + 'deg)';
        });
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }
})();
