/* Tasty Pizza — brand direction behaviour.

   Small on purpose. Page speed is a conversion lever on a takeaway site (a 1s
   load converts around 40%, a 3s load around 29%), so the reveals and the
   turntable are CSS scroll-driven animations running on the compositor, and
   this file only does what CSS cannot:

     1. Lenis, for the smooth wheel (3KB)
     2. the reveal fallback for browsers without scroll timelines (~16%)
     3. the open/closed clock, in Halifax time
     4. the phone sheet
     5. the pizza builder

   No animation framework. 60KB to fade cards in would be indefensible here. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var money = function (n) { return '$' + (Math.round(n * 100) / 100).toFixed(2); };

  /* ------------------------------------------------------------ smooth wheel */
  if (!calm && typeof Lenis !== 'undefined') {
    window.__lenis = new Lenis({ lerp: 0.085, wheelMultiplier: 0.95, anchors: true,
      autoRaf: true, autoToggle: true });
  }

  /* ------------------------------------------------------------ reveal fallback */
  if (!calm && !(window.CSS && CSS.supports && CSS.supports('animation-timeline', 'view()'))
      && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('in');
        io.unobserve(en.target);
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -8% 0px' });
    $$('[data-anim],[data-stagger]').forEach(function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------------ open / closed
     Always answered in Halifax time — someone checking from away still needs to
     know whether this kitchen is on right now. */
  var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  function halifaxNow() {
    try {
      var p = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Halifax', weekday: 'long',
        hour: 'numeric', minute: 'numeric', hour12: false }).formatToParts(new Date());
      var o = {};
      p.forEach(function (x) { o[x.type] = x.value; });
      return { day: o.weekday, mins: (parseInt(o.hour, 10) % 24) * 60 + parseInt(o.minute, 10) };
    } catch (e) {
      var d = new Date();
      return { day: DAYS[d.getDay()], mins: d.getHours() * 60 + d.getMinutes() };
    }
  }

  function hhmm(m) {
    var h = Math.floor(m / 60) % 24, mm = m % 60;
    return (h % 12 || 12) + (mm ? ':' + (mm < 10 ? '0' : '') + mm : '') + (h < 12 ? 'am' : 'pm');
  }

  function paintClock() {
    var hours = window.HOURS || [];
    if (!hours.length) return;
    var now = halifaxNow(), idx = DAYS.indexOf(now.day), by = {};
    hours.forEach(function (h) { by[h.day] = h; });

    var txt, shut = true;
    // yesterday's shift can still be running (Friday closes at 2am Saturday)
    var prev = by[DAYS[(idx + 6) % 7]];
    var today = by[now.day];
    if (prev && !prev.closed && prev.close > 24 && now.mins < (prev.close - 24) * 60) {
      shut = false; txt = 'Open till ' + hhmm((prev.close - 24) * 60);
    } else if (today && !today.closed && now.mins >= today.open * 60 && now.mins < today.close * 60) {
      shut = false; txt = 'Open till ' + hhmm(today.close * 60);
    } else if (today && !today.closed && now.mins < today.open * 60) {
      txt = 'Opens ' + hhmm(today.open * 60);
    } else {
      var nxt = null;
      for (var i = 1; i <= 7 && !nxt; i++) {
        var d = by[DAYS[(idx + i) % 7]];
        if (d && !d.closed) nxt = { day: i === 1 ? 'tomorrow' : d.day, at: d.open };
      }
      txt = nxt ? 'Opens ' + nxt.day + ' ' + hhmm(nxt.at * 60) : 'Closed';
    }

    $$('[data-clock]').forEach(function (el) {
      el.textContent = txt;
      if (shut) el.setAttribute('data-shut', ''); else el.removeAttribute('data-shut');
    });
    $$('.hours div').forEach(function (r) {
      if (r.getAttribute('data-day') === now.day) r.setAttribute('data-today', '');
      else r.removeAttribute('data-today');
    });
  }

  /* ------------------------------------------------------------ phone sheet */
  var dots = $('[data-sheet-toggle]'), sheet = $('[data-sheet]');
  if (dots && sheet) {
    dots.addEventListener('click', function () {
      var open = sheet.hasAttribute('data-open');
      if (open) sheet.removeAttribute('data-open'); else sheet.setAttribute('data-open', '');
      dots.setAttribute('aria-expanded', String(!open));
    });
    sheet.addEventListener('click', function (ev) {
      if (ev.target.closest('a')) {
        sheet.removeAttribute('data-open');
        dots.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('click', function (ev) {
      if (!sheet.contains(ev.target) && !dots.contains(ev.target)) {
        sheet.removeAttribute('data-open');
        dots.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ------------------------------------------------------------ add feedback
     No cart in this study — the button confirms so the interaction reads as
     real while the ordering platform decision is still open. */
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-add]');
    if (!b) return;
    var was = b.textContent;
    b.setAttribute('data-done', '');
    b.textContent = 'Added';
    setTimeout(function () { b.removeAttribute('data-done'); b.textContent = was; }, 1200);
  });

  /* ------------------------------------------------------------ the builder */
  var B = { size: 1, crust: 'White', sur: 0, tops: [] };
  var CFG = window.BUILD;

  function state() {
    var n = Math.min(B.tops.length, CFG.prices.length - 1);
    var price = CFG.prices[n][B.size] + (B.sur || 0);
    var label = !B.tops.length ? 'just cheese'
      : (B.tops.length >= CFG.max ? CFG.special
        : B.tops.length + ' topping' + (B.tops.length > 1 ? 's' : ''));
    return { price: price, note: CFG.sizes[B.size] + ' · ' + label };
  }

  function paint(bump) {
    var st = state();
    var p = $('[data-price]');
    if (p) {
      p.textContent = money(st.price);
      if (bump) { p.setAttribute('data-bump', ''); setTimeout(function () { p.removeAttribute('data-bump'); }, 320); }
    }
    var note = $('[data-note]');
    if (note) note.textContent = st.note;
    var c = $('[data-count]');
    if (c) c.textContent = B.tops.length + ' of ' + CFG.max;
    var dough = $('[data-dough]');
    if (dough) {
      if (B.tops.length) dough.setAttribute('data-topped', ''); else dough.removeAttribute('data-topped');
      dough.style.width = [78, 86, 94, 100][B.size] + '%';
    }
    $$('.topbtn').forEach(function (btn) {
      var on = B.tops.indexOf(btn.getAttribute('data-top')) >= 0;
      btn.setAttribute('aria-pressed', String(on));
      if (!on && B.tops.length >= CFG.max) btn.setAttribute('data-full', '');
      else btn.removeAttribute('data-full');
    });
  }

  function sprinkle(name) {
    var host = $('[data-tops]'), look = window.TOPPING_LOOK[name];
    if (!host || !look) return;
    for (var i = 0; i < 7; i++) {
      var bit = document.createElement('span');
      bit.className = 'bit';
      bit.setAttribute('data-for', name);
      var ang = i * 2.399 + Math.random() * 0.7;
      var rad = 13 + Math.sqrt((i + 0.55) / 7) * 31;
      bit.style.left = (50 + Math.cos(ang) * rad) + '%';
      bit.style.top = (50 + Math.sin(ang) * rad) + '%';
      bit.style.setProperty('--w', (look.size * (0.86 + Math.random() * 0.28)).toFixed(1) + 'px');
      bit.style.setProperty('--rot', Math.round(Math.random() * 360) + 'deg');
      bit.style.animationDelay = (i * 38) + 'ms';
      bit.innerHTML = '<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">' + look.svg + '</svg>';
      host.appendChild(bit);
    }
  }

  function unsprinkle(name) {
    $$('[data-tops] .bit').forEach(function (b) {
      if (b.getAttribute('data-for') === name) b.remove();
    });
  }

  function initBuilder() {
    var grid = $('[data-topgrid]');
    if (!grid || !CFG) return;

    // one source of truth for topping colour: the swatch and the piece that
    // lands on the dough come from the same table
    $$('.topbtn').forEach(function (b) {
      var look = window.TOPPING_LOOK[b.getAttribute('data-top')];
      var dot = b.querySelector('.tdot');
      if (look && dot) dot.style.background = look.c;
    });

    $$('[data-sizes] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        B.size = parseInt(b.getAttribute('data-size'), 10);
        $$('[data-sizes] .chip').forEach(function (o) {
          if (o === b) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
        });
        paint(true);
      });
    });
    $$('[data-crusts] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        B.crust = b.getAttribute('data-crust');
        B.sur = parseFloat(b.getAttribute('data-sur')) || 0;
        $$('[data-crusts] .chip').forEach(function (o) {
          if (o === b) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
        });
        paint(true);
      });
    });
    grid.addEventListener('click', function (ev) {
      var b = ev.target.closest('.topbtn');
      if (!b) return;
      var name = b.getAttribute('data-top'), at = B.tops.indexOf(name);
      if (at >= 0) { B.tops.splice(at, 1); unsprinkle(name); }
      else {
        if (B.tops.length >= CFG.max) return;
        B.tops.push(name);
        sprinkle(name);
      }
      paint(true);
    });
    paint(false);
  }

  paintClock();
  setInterval(paintClock, 60000);
  initBuilder();
})();
