/* Tasty Pizza — interaction layer.
   No framework, no build step. Everything degrades: with JS off the page is a
   complete, readable, callable menu. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var money = function (n) { return '$' + (Math.round(n * 100) / 100).toFixed(2); };

  /* ------------------------------------------------------------ open now
     Always answered in Halifax time, not the visitor's — someone checking from
     Toronto still needs to know whether this kitchen is on. */
  var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  function halifaxNow() {
    try {
      var p = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/Halifax', weekday: 'long', hour: 'numeric',
        minute: 'numeric', hour12: false
      }).formatToParts(new Date());
      var o = {};
      p.forEach(function (x) { o[x.type] = x.value; });
      return { day: o.weekday, h: parseInt(o.hour, 10) % 24, m: parseInt(o.minute, 10) };
    } catch (err) {
      var d = new Date();
      return { day: DAYS[d.getDay()], h: d.getHours(), m: d.getMinutes() };
    }
  }

  function openState() {
    var hours = window.HOURS || [];
    if (!hours.length) return null;
    var now = halifaxNow();
    var idx = DAYS.indexOf(now.day);
    var mins = now.h * 60 + now.m;
    var byDay = {};
    hours.forEach(function (h) { byDay[h.day] = h; });

    // Yesterday's shift can still be running (Friday closes at 2am Saturday).
    var prev = byDay[DAYS[(idx + 6) % 7]];
    if (prev && !prev.closed && prev.close > 24 && mins < (prev.close - 24) * 60) {
      return { open: true, until: (prev.close - 24) * 60, closingSoon: (prev.close - 24) * 60 - mins <= 45 };
    }
    var today = byDay[now.day];
    if (!today || today.closed) return { open: false, next: nextOpen(byDay, idx) };
    var o = today.open * 60, c = today.close * 60;
    if (mins >= o && mins < c) {
      return { open: true, until: c, closingSoon: c - mins <= 45 };
    }
    if (mins < o) return { open: false, next: { day: 'today', at: today.open } };
    return { open: false, next: nextOpen(byDay, idx) };
  }

  function nextOpen(byDay, idx) {
    for (var i = 1; i <= 7; i++) {
      var d = byDay[DAYS[(idx + i) % 7]];
      if (d && !d.closed) return { day: i === 1 ? 'tomorrow' : d.day, at: d.open };
    }
    return null;
  }

  function hhmm(mins) {
    var h = Math.floor(mins / 60) % 24, m = mins % 60;
    var ap = h < 12 ? 'am' : 'pm', d = (h % 12) || 12;
    return d + (m ? ':' + (m < 10 ? '0' : '') + m : '') + ap;
  }

  function paintClock() {
    var st = openState();
    if (!st) return;
    var txt, shut = !st.open;
    if (st.open) {
      txt = st.closingSoon ? 'Closing at ' + hhmm(st.until) : 'Open now until ' + hhmm(st.until);
    } else if (st.next) {
      txt = 'Closed — opens ' + (st.next.day === 'today' ? '' : st.next.day + ' ') + 'at ' + hhmm(st.next.at * 60);
    } else {
      txt = 'Closed';
    }
    $$('[data-clock]').forEach(function (el) {
      el.textContent = txt;
      el.hidden = false;
      if (shut) el.setAttribute('data-shut', ''); else el.removeAttribute('data-shut');
    });
    var today = halifaxNow().day;
    $$('.hrow').forEach(function (r) {
      if (r.getAttribute('data-day') === today) r.setAttribute('data-today', '');
      else r.removeAttribute('data-today');
    });
  }

  /* ------------------------------------------------------------ nav drawer */
  var burger = $('.burger'), drawer = $('.drawer');
  if (burger && drawer) {
    burger.addEventListener('click', function () {
      var open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!open));
      drawer.hidden = open;
      document.body.style.overflow = open ? '' : 'hidden';
    });
    drawer.addEventListener('click', function (ev) {
      if (ev.target.closest('a')) {
        burger.setAttribute('aria-expanded', 'false');
        drawer.hidden = true;
        document.body.style.overflow = '';
      }
    });
  }

  /* ------------------------------------------------------------ the tray
     Not a checkout. It's a list you build by tapping, then read out on the
     phone, copy, or email. Honest about what it is. */
  var KEY = 'tp.order.v1';
  var order = [];
  try { order = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { order = []; }
  if (!Array.isArray(order)) order = [];

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(order)); } catch (e) { /* private mode */ }
  }

  function total() {
    return order.reduce(function (s, r) { return s + (r.price || 0) * r.qty; }, 0);
  }

  function countItems() {
    return order.reduce(function (s, r) { return s + r.qty; }, 0);
  }

  function addToOrder(name, price) {
    var found = null;
    order.forEach(function (r) { if (r.name === name && r.price === price) found = r; });
    if (found) found.qty += 1;
    else order.push({ name: name, price: price, qty: 1 });
    save();
    renderTray();
  }

  function setQty(i, q) {
    if (q <= 0) order.splice(i, 1); else order[i].qty = q;
    save();
    renderTray();
  }

  function orderText() {
    var lines = order.map(function (r) {
      return r.qty + ' x ' + r.name + (r.price ? '  ' + money(r.price * r.qty) : '');
    });
    lines.push('');
    lines.push('Total before tax: ' + money(total()));
    return lines.join('\n');
  }

  function renderTray() {
    var tray = $('[data-tray]');
    if (!tray) return;
    var n = countItems();
    tray.hidden = n === 0;
    var callbar = $('.callbar');
    if (callbar) callbar.style.display = n > 0 && window.innerWidth <= 860 ? 'none' : '';

    $$('[data-tray-total]').forEach(function (el) { el.textContent = money(total()); });
    var c = $('[data-tray-count]');
    if (c) c.textContent = String(n);
    var label = $('.tray-label');
    if (label) label.textContent = n === 1 ? 'Your order' : 'Your order';

    var list = $('[data-tray-list]');
    if (!list) return;
    if (!order.length) {
      list.innerHTML = '<li class="tray-empty">Nothing here yet. Tap a price on the menu.</li>';
    } else {
      list.innerHTML = order.map(function (r, i) {
        return '<li class="tray-row">' +
          '<div class="qty"><button type="button" data-q="' + i + '" data-d="-1" aria-label="One fewer">' + svg('minus') + '</button>' +
          '<span>' + r.qty + '</span>' +
          '<button type="button" data-q="' + i + '" data-d="1" aria-label="One more">' + svg('plus') + '</button></div>' +
          '<span class="n">' + esc(r.name) + '</span>' +
          '<span class="p">' + (r.price ? money(r.price * r.qty) : 'ask') + '</span></li>';
      }).join('');
    }
    var acts = $('[data-tray-acts]');
    if (acts && !acts.dataset.built) {
      var S = window.SITE || {};
      var html = '<a class="btn btn-red big" href="tel:' + S.phoneLink + '">Call ' + S.phone + ' to order</a>' +
        '<button class="btn btn-bone" type="button" data-copy>Copy my order</button>' +
        '<a class="btn btn-ghost" data-mail href="#">Email it to the shop</a>';
      if (S.doordash) html += '<a class="btn btn-ghost" href="' + S.doordash + '" target="_blank" rel="noopener">Order on DoorDash</a>';
      if (S.ubereats) html += '<a class="btn btn-ghost" href="' + S.ubereats + '" target="_blank" rel="noopener">Order on Uber Eats</a>';
      acts.innerHTML = html;
      acts.dataset.built = '1';
    }
    var mail = $('[data-mail]');
    if (mail) {
      var S2 = window.SITE || {};
      mail.href = 'mailto:' + S2.email + '?subject=' + encodeURIComponent('Order from the website') +
        '&body=' + encodeURIComponent(orderText() + '\n\nName:\nPhone:\nPickup or delivery:\n');
    }
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function svg(n) {
    var p = n === 'plus' ? '<path d="M12 6v12M6 12h12"/>' : '<path d="M6 12h12"/>';
    return '<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">' + p + '</svg>';
  }

  document.addEventListener('click', function (ev) {
    var add = ev.target.closest('[data-add]');
    if (add) {
      var price = add.getAttribute('data-price');
      var name = add.getAttribute('data-add');
      // a deal with its add-on ticked is a different line
      var deal = add.closest('.deal');
      if (deal) {
        var box = deal.querySelector('[data-addon]');
        if (box && box.checked) {
          price = String(parseFloat(price || 0) + parseFloat(box.getAttribute('data-addon')));
          name = name + ' + ' + box.parentNode.querySelector('span').textContent.split(' +')[0].trim();
        }
      }
      if (add.id === 'buildAdd' || add.getAttribute('data-add') === 'Custom pizza') {
        var b = buildState();
        name = b.label;
        price = String(b.price);
      }
      addToOrder(name, price === '' || price === null ? null : parseFloat(price));
      flash(add);
      return;
    }
    var q = ev.target.closest('[data-q]');
    if (q) {
      var i = parseInt(q.getAttribute('data-q'), 10);
      setQty(i, order[i].qty + parseInt(q.getAttribute('data-d'), 10));
      return;
    }
    if (ev.target.closest('[data-tray-toggle]')) { openSheet(true); return; }
    if (ev.target.closest('[data-tray-close]')) { openSheet(false); return; }
    if (ev.target.closest('[data-tray-scrim]')) { openSheet(false); return; }
    if (ev.target.closest('[data-tray-clear]')) { order = []; save(); renderTray(); openSheet(false); return; }
    var cp = ev.target.closest('[data-copy]');
    if (cp) {
      var t = orderText();
      var done = function () { cp.textContent = 'Copied'; setTimeout(function () { cp.textContent = 'Copy my order'; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(t).then(done, done);
      else done();
      return;
    }
  });

  function flash(btn) {
    btn.setAttribute('data-done', '');
    var span = btn.querySelector('span');
    var was = span ? span.textContent : null;
    if (span) span.textContent = 'Added';
    setTimeout(function () {
      btn.removeAttribute('data-done');
      if (span && was !== null) span.textContent = was;
    }, 1100);
  }

  function openSheet(on) {
    var sheet = $('[data-tray-sheet]'), scrim = $('[data-tray-scrim]');
    if (!sheet) return;
    sheet.hidden = !on;
    if (scrim) scrim.hidden = !on;
    document.body.style.overflow = on ? 'hidden' : '';
  }

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') openSheet(false);
  });

  /* deal add-on re-prices its card in place */
  $$('[data-addon]').forEach(function (box) {
    box.addEventListener('change', function () {
      var card = box.closest('.deal');
      var el = card.querySelector('[data-deal-price]');
      var base = parseFloat(el.getAttribute('data-deal-price'));
      el.textContent = money(box.checked ? base + parseFloat(box.getAttribute('data-addon')) : base);
    });
  });

  /* ------------------------------------------------------------ the builder */
  var TOPPING_LOOK = {
    'Pepperoni': { c: '#C0392B', w: 17, br: '50%' },
    'Salami': { c: '#9E3B36', w: 16, br: '50%' },
    'Mushrooms': { c: '#C9B79B', w: 15, br: '42% 58% 50% 50%' },
    'Green Peppers': { c: '#3E8E41', w: 16, h: 7, br: '99px' },
    'Red Peppers': { c: '#CF4520', w: 16, h: 7, br: '99px' },
    'Onions': { c: '#F2E6D8', w: 17, h: 5, br: '99px' },
    'Red Onions': { c: '#9C6B9E', w: 17, h: 5, br: '99px' },
    'Bacon': { c: '#A8503A', w: 14, h: 7, br: '3px' },
    'Hamburger': { c: '#7B4B2A', w: 11, br: '45%' },
    'Tomatoes': { c: '#D64031', w: 14, br: '50%' },
    'Pineapple': { c: '#F0C233', w: 13, br: '4px' },
    'Italian Sausage': { c: '#8C4A2F', w: 12, br: '50%' },
    'Hot Peppers': { c: '#2E7D32', w: 13, h: 6, br: '99px' },
    'Black Olives': { c: '#2B2430', w: 12, br: '50%' },
    'Green Olives': { c: '#7D8F3A', w: 12, br: '50%' },
    'Donair Meat': { c: '#8A5A34', w: 16, h: 8, br: '3px' },
    'Ham': { c: '#E29A9A', w: 15, h: 8, br: '3px' }
  };

  var B = { size: 1, crust: 'White', sur: 0, tops: [] };
  var PRICES = null, SIZE_NAMES = [], MAXT = 5, SPECIAL = 'Tasty Pizza Special';

  function buildState() {
    var n = Math.min(B.tops.length, PRICES ? PRICES.length - 1 : 5);
    var base = PRICES ? PRICES[n][B.size] : 0;
    var price = base + (B.sur || 0);
    var label;
    if (!B.tops.length) label = SIZE_NAMES[B.size] + ' cheese pizza';
    else if (B.tops.length >= MAXT) label = SIZE_NAMES[B.size] + ' ' + SPECIAL;
    else label = SIZE_NAMES[B.size] + ' pizza, ' + B.tops.length + ' topping' + (B.tops.length > 1 ? 's' : '');
    if (B.crust !== 'White') label += ' (' + B.crust + ')';
    if (B.tops.length) label += ' — ' + B.tops.join(', ');
    return { price: price, label: label, base: base };
  }

  function paintBuild(bump) {
    var st = buildState();
    var pe = $('[data-build-price]');
    if (pe) {
      pe.textContent = money(st.price);
      if (bump) {
        pe.setAttribute('data-bump', '');
        setTimeout(function () { pe.removeAttribute('data-bump'); }, 320);
      }
    }
    var ne = $('[data-build-note]');
    if (ne) {
      var bits = [SIZE_NAMES[B.size], B.crust.toLowerCase() + ' crust'];
      bits.push(B.tops.length ? (B.tops.length >= MAXT ? SPECIAL : B.tops.length + ' topping' + (B.tops.length > 1 ? 's' : '')) : 'just cheese');
      ne.textContent = bits.join(' · ');
    }
    var cnt = $('[data-top-count]');
    if (cnt) cnt.textContent = B.tops.length + ' of ' + MAXT;
    var dough = $('[data-dough]');
    if (dough) {
      if (B.tops.length) dough.setAttribute('data-topped', ''); else dough.removeAttribute('data-topped');
      dough.style.width = [78, 86, 94, 100][B.size] + '%';
    }
    $$('[data-topgrid] .topbtn').forEach(function (b) {
      var on = B.tops.indexOf(b.getAttribute('data-top')) >= 0;
      b.setAttribute('aria-pressed', String(on));
      if (!on && B.tops.length >= MAXT) b.setAttribute('data-full', ''); else b.removeAttribute('data-full');
    });
  }

  function sprinkle(name) {
    var host = $('[data-tops]');
    if (!host) return;
    var look = TOPPING_LOOK[name] || { c: '#B85', w: 14, br: '50%' };
    var n = 7;
    for (var i = 0; i < n; i++) {
      var bit = document.createElement('i');
      bit.className = 'bit';
      bit.setAttribute('data-for', name);
      // even-ish scatter: golden angle, jittered
      var a = (i * 2.399 + Math.random() * 0.7);
      var r = 14 + Math.sqrt((i + 0.6) / n) * 31;
      bit.style.left = (50 + Math.cos(a) * r) + '%';
      bit.style.top = (50 + Math.sin(a) * r) + '%';
      bit.style.setProperty('--c', look.c);
      bit.style.setProperty('--w', look.w + 'px');
      bit.style.setProperty('--h', (look.h || look.w) + 'px');
      bit.style.setProperty('--br', look.br);
      bit.style.setProperty('--rot', Math.round(Math.random() * 360) + 'deg');
      bit.style.animationDelay = (i * 32) + 'ms';
      host.appendChild(bit);
    }
  }

  function unsprinkle(name) {
    $$('[data-tops] .bit').forEach(function (b) {
      if (b.getAttribute('data-for') === name) b.remove();
    });
  }

  function cheer() {
    var c = $('[data-chef]');
    if (!c) return;
    c.setAttribute('data-cheer', '');
    setTimeout(function () { c.removeAttribute('data-cheer'); }, 560);
  }

  function initBuilder() {
    var grid = $('[data-topgrid]');
    if (!grid) return;
    PRICES = window.BUILD && window.BUILD.priceByToppingCount;
    SIZE_NAMES = (window.BUILD && window.BUILD.sizes) || [];
    MAXT = (window.BUILD && window.BUILD.maxToppings) || 5;
    SPECIAL = (window.BUILD && window.BUILD.specialName) || SPECIAL;

    // one source of truth for topping colour: the swatch and the bits that land
    // on the dough are coloured from the same table
    $$('.topbtn').forEach(function (b) {
      var look = TOPPING_LOOK[b.getAttribute('data-top')];
      var dot = b.querySelector('.tdot');
      if (look && dot) dot.style.background = look.c;
    });

    $$('[data-sizes] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        B.size = parseInt(b.getAttribute('data-size'), 10);
        $$('[data-sizes] .chip').forEach(function (o) {
          var on = o === b;
          if (on) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
          o.setAttribute('aria-checked', String(on));
        });
        paintBuild(true);
      });
    });
    $$('[data-crusts] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        B.crust = b.getAttribute('data-crust');
        B.sur = parseFloat(b.getAttribute('data-sur')) || 0;
        $$('[data-crusts] .chip').forEach(function (o) {
          var on = o === b;
          if (on) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
          o.setAttribute('aria-checked', String(on));
        });
        paintBuild(true);
      });
    });
    grid.addEventListener('click', function (ev) {
      var b = ev.target.closest('.topbtn');
      if (!b) return;
      var name = b.getAttribute('data-top');
      var at = B.tops.indexOf(name);
      if (at >= 0) {
        B.tops.splice(at, 1);
        unsprinkle(name);
      } else {
        if (B.tops.length >= MAXT) {
          b.animate ? b.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-5px)' },
            { transform: 'translateX(5px)' }, { transform: 'translateX(0)' }], { duration: 240 }) : null;
          return;
        }
        B.tops.push(name);
        sprinkle(name);
        if (B.tops.length === MAXT) cheer();
      }
      paintBuild(true);
    });
    var reset = $('[data-build-reset]');
    if (reset) {
      reset.addEventListener('click', function () {
        B.tops.slice().forEach(unsprinkle);
        B.tops = [];
        paintBuild(true);
      });
    }
    paintBuild(false);
  }

  /* ------------------------------------------------------------ menu filter */
  function initMenu() {
    var search = $('[data-search]');
    if (!search) return;
    var rows = $$('[data-item]');
    var active = [];

    function apply() {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (r) {
        var tags = (r.getAttribute('data-tags') || '').split(' ');
        var okTag = !active.length || active.every(function (t) { return tags.indexOf(t) >= 0; });
        var hay = (r.getAttribute('data-name') || '') + ' ' + r.textContent.toLowerCase();
        var okQ = !q || hay.indexOf(q) >= 0;
        var on = okTag && okQ;
        r.hidden = !on;
        if (on) shown++;
      });
      // hide groups and categories that have nothing left in them
      $$('.grp').forEach(function (g) {
        var any = $$('[data-item]', g).some(function (r) { return !r.hidden; });
        if ($$('[data-item]', g).length) g.hidden = !any;
      });
      var filtering = !!q || active.length > 0;
      $$('.cat').forEach(function (c) {
        var rowsIn = $$('[data-item]', c).length;
        if (!rowsIn) { c.hidden = filtering; return; }
        c.hidden = !$$('.grp', c).some(function (g) { return !g.hidden; });
      });
      var nr = $('[data-noresult]');
      if (nr) nr.hidden = shown > 0;
      var x = $('[data-search-clear]');
      if (x) x.hidden = !q;
    }

    search.addEventListener('input', apply);
    $$('[data-search-clear]').forEach(function (b) {
      b.addEventListener('click', function () {
        search.value = '';
        active = [];
        $$('[data-filter]').forEach(function (f) { f.removeAttribute('data-on'); });
        apply();
        search.focus();
      });
    });
    $$('[data-filter]').forEach(function (f) {
      f.addEventListener('click', function () {
        var t = f.getAttribute('data-filter');
        var at = active.indexOf(t);
        if (at >= 0) { active.splice(at, 1); f.removeAttribute('data-on'); }
        else { active.push(t); f.setAttribute('data-on', ''); }
        apply();
      });
    });

    // which category the reader is in
    var rail = $$('.railitem');
    if (rail.length && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var id = en.target.id;
          rail.forEach(function (a) {
            if (a.getAttribute('href') === '#' + id) a.setAttribute('data-on', '');
            else a.removeAttribute('data-on');
          });
        });
      }, { rootMargin: '-180px 0px -70% 0px' });
      $$('.cat').forEach(function (c) { io.observe(c); });
    }

    // size columns need to know how many columns they have
    $$('.sizecols').forEach(function (el) {
      el.style.setProperty('--n', el.children.length);
    });
  }

  /* ------------------------------------------------------------ go */
  paintClock();
  setInterval(paintClock, 60000);
  renderTray();
  initBuilder();
  initMenu();
})();
