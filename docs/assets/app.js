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

  /* ------------------------------------------------------------ hero + header */
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');

  (function heroVideo() {
    var v = $('[data-hero-video]');
    if (!v) return;
    if (calm && calm.matches) {
      v.removeAttribute('autoplay');
      v.pause();
      return;
    }
    // Some browsers refuse autoplay until the element is muted in JS as well.
    v.muted = true;
    var go = v.play();
    if (go && go.catch) go.catch(function () { /* poster stands in */ });
    // don't burn battery decoding a video nobody can see
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        es.forEach(function (en) {
          if (en.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
          else v.pause();
        });
      }, { threshold: 0.05 }).observe(v);
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) v.pause();
      else { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    });
  })();

  (function stickyHeader() {
    var top = $('.top');
    if (!top) return;
    var on = false;
    var paint = function () {
      var want = window.scrollY > 8;
      if (want !== on) {
        on = want;
        if (on) top.setAttribute('data-stuck', ''); else top.removeAttribute('data-stuck');
      }
    };
    paint();
    window.addEventListener('scroll', paint, { passive: true });
  })();

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
  /* Each topping is drawn, not approximated with a coloured dot: pepperoni cups at
     the edge and has fat flecks, peppers are rings, olives have holes, onion is a
     translucent sliver. `c` is the swatch colour shown on the button. */
  var TOPPING_LOOK = {
    'Pepperoni': { c: '#C23B2B', size: 30, svg:
      '<circle cx="16" cy="16" r="14" fill="#A8291C"/><circle cx="16" cy="16" r="12.4" fill="#CC4630"/>' +
      '<circle cx="16" cy="16" r="10.4" fill="#D9573C"/>' +
      '<ellipse cx="12" cy="12" rx="2.1" ry="1.7" fill="#8E2318" opacity=".62"/>' +
      '<ellipse cx="20" cy="14.5" rx="1.7" ry="1.4" fill="#8E2318" opacity=".55"/>' +
      '<ellipse cx="15" cy="21" rx="1.9" ry="1.5" fill="#8E2318" opacity=".5"/>' +
      '<ellipse cx="12" cy="11" rx="4.5" ry="3" fill="#F08A6A" opacity=".3"/>' },
    'Salami': { c: '#96332F', size: 28, svg:
      '<circle cx="16" cy="16" r="14" fill="#7E2926"/><circle cx="16" cy="16" r="12.2" fill="#9C3934"/>' +
      '<circle cx="11.5" cy="13" r="1.9" fill="#F2DCCF" opacity=".78"/>' +
      '<circle cx="20" cy="12.5" r="1.5" fill="#F2DCCF" opacity=".7"/>' +
      '<circle cx="18" cy="20.5" r="1.7" fill="#F2DCCF" opacity=".72"/>' +
      '<circle cx="12" cy="20" r="1.2" fill="#F2DCCF" opacity=".6"/>' },
    'Mushrooms': { c: '#C2AD8E', size: 27, svg:
      '<path d="M4 18c0-7 5.4-12 12-12s12 5 12 12c0 2-2 3-5 3H9c-3 0-5-1-5-3Z" fill="#D9C7A8"/>' +
      '<path d="M11 21h10c0 4-2 6-5 6s-5-2-5-6Z" fill="#EFE3CC"/>' +
      '<path d="M8 19h16M12 19.4l-.6 2M20 19.4l.6 2" stroke="#B49C77" stroke-width="1.1" stroke-linecap="round"/>' +
      '<path d="M9 12c3-3 8-4 12-2" stroke="#EDDFC4" stroke-width="1.6" stroke-linecap="round" opacity=".7"/>' },
    'Green Peppers': { c: '#3E8E41', size: 26, svg:
      '<path d="M16 3a13 13 0 1 1 0 26 13 13 0 0 1 0-26Zm0 5a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z" fill="#3D8B3F"/>' +
      '<path d="M16 4.6a11.4 11.4 0 0 1 9 4.4" stroke="#6FBF6B" stroke-width="2" stroke-linecap="round" fill="none" opacity=".75"/>' },
    'Red Peppers': { c: '#CE4A22', size: 26, svg:
      '<path d="M16 3a13 13 0 1 1 0 26 13 13 0 0 1 0-26Zm0 5a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z" fill="#C8461F"/>' +
      '<path d="M16 4.6a11.4 11.4 0 0 1 9 4.4" stroke="#EE7A4C" stroke-width="2" stroke-linecap="round" fill="none" opacity=".75"/>' },
    'Onions': { c: '#EFE2D2', size: 30, svg:
      '<path d="M3 20a13 13 0 0 1 26 0" stroke="#F4EADC" stroke-width="3.2" fill="none" stroke-linecap="round" opacity=".92"/>' +
      '<path d="M7 20a9 9 0 0 1 18 0" stroke="#E2D2BE" stroke-width="2" fill="none" stroke-linecap="round" opacity=".8"/>' },
    'Red Onions': { c: '#9A6C9E', size: 30, svg:
      '<path d="M3 20a13 13 0 0 1 26 0" stroke="#A375A6" stroke-width="3.2" fill="none" stroke-linecap="round" opacity=".92"/>' +
      '<path d="M7 20a9 9 0 0 1 18 0" stroke="#C9A8CB" stroke-width="2" fill="none" stroke-linecap="round" opacity=".85"/>' },
    'Bacon': { c: '#A8503A', size: 28, svg:
      '<path d="M2 12c5-5 9 3 14-1s9 2 14-2v9c-5 4-9-2-14 2s-9-4-14 1Z" fill="#A8503A"/>' +
      '<path d="M2 14.5c5-5 9 3 14-1s9 2 14-2" stroke="#EBC7B2" stroke-width="1.8" fill="none" opacity=".72"/>' +
      '<path d="M2 19c5-5 9 3 14-1s9 2 14-2" stroke="#7E3527" stroke-width="1.3" fill="none" opacity=".55"/>' },
    'Hamburger': { c: '#7B4B2A', size: 26, svg:
      '<path d="M6 14c0-2.6 2.3-4.3 4.6-3.6 1.3-2.2 4.6-2.4 6-.4 2.6-1 5.4.8 5.4 3.4 2.2.5 3 3.2 1.4 4.8-.6 2.6-3.6 3.6-5.6 2.2-1.7 1.6-4.7 1.3-6-.6-2.6.5-5-1.6-4.8-4.2Z" fill="#7A4826"/>' +
      '<path d="M10 13.5c1.6-1.2 3.6-.6 4.4 1M18 12.6c1.8-.3 3 .8 3.2 2.3" stroke="#A9754C" stroke-width="1.5" stroke-linecap="round" fill="none"/>' +
      '<circle cx="12" cy="17.6" r="1.7" fill="#5E3117" opacity=".55"/>' +
      '<circle cx="18.6" cy="18.4" r="1.4" fill="#5E3117" opacity=".45"/>' +
      '<circle cx="15.4" cy="14.6" r="1.2" fill="#9C6841" opacity=".8"/>' },
    'Tomatoes': { c: '#D64031', size: 26, svg:
      '<circle cx="16" cy="16" r="13" fill="#CE3A2C"/><circle cx="16" cy="16" r="10.6" fill="#E45744"/>' +
      '<path d="M16 6.5v19M6.5 16h19M9 9l14 14M23 9 9 23" stroke="#F4A092" stroke-width="1.5" opacity=".45"/>' +
      '<circle cx="16" cy="16" r="3.4" fill="#F2AFA2" opacity=".7"/>' },
    // a wedge cut from a pineapple ring: the notched inner edge and the fibre fan
    // keep it distinct from the olives and peppers, which are full rings
    'Pineapple': { c: '#F0C233', size: 26, svg:
      '<path d="M16 19.8a4.2 4.2 0 0 1 3.9-4.2l9.3-.7a1.6 1.6 0 0 1 1.7 1.9 15.6 15.6 0 0 1-11.6 12 1.6 1.6 0 0 1-2-1.6Z" ' +
      'transform="rotate(-140 16 16)" fill="#D79A12"/>' +
      '<path d="M16 19.8a3.4 3.4 0 0 1 3.2-3.4l8.8-.6a1.2 1.2 0 0 1 1.3 1.4 14.2 14.2 0 0 1-10.6 10.9 1.2 1.2 0 0 1-1.5-1.2Z" ' +
      'transform="rotate(-140 16 16)" fill="#F7CE42"/>' +
      '<g transform="rotate(-140 16 16)" stroke="#CE9410" stroke-width=".85" stroke-linecap="round" opacity=".62">' +
      '<path d="M18.6 19.6 27.4 19"/><path d="M19.6 22.8 26.8 21.4"/><path d="M21.3 25.4 25.6 23.4"/></g>' +
      '<path d="M16 19.8a3.4 3.4 0 0 1 3.2-3.4" transform="rotate(-140 16 16)" stroke="#FCEBAE" stroke-width="1.3" fill="none" stroke-linecap="round"/>' },
    'Italian Sausage': { c: '#8C4A2F', size: 25, svg:
      '<path d="M8.4 12.6c.6-3 4-4.6 6.6-3.4 2.4-1.7 6-.4 6.8 2.4 2.7 1 3.2 4.8 1 6.6.2 3-3 5.2-5.7 4-2.3 1.9-5.9.9-7-1.8-2.9-.6-4-4.4-1.7-6.4Z" fill="#8A472D"/>' +
      '<circle cx="12.6" cy="14" r="1.5" fill="#C08A63" opacity=".85"/>' +
      '<circle cx="19.4" cy="14.8" r="1.2" fill="#C08A63" opacity=".75"/>' +
      '<circle cx="15.8" cy="19.4" r="1.6" fill="#5C2D18" opacity=".6"/>' +
      '<circle cx="19.8" cy="19.2" r="1" fill="#C08A63" opacity=".6"/>' +
      '<circle cx="13.4" cy="18.4" r=".9" fill="#5C2D18" opacity=".5"/>' },
    'Hot Peppers': { c: '#2E7D32', size: 22, svg:
      '<path d="M16 5a11 11 0 1 1 0 22 11 11 0 0 1 0-22Zm0 4.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Z" fill="#2F7D33"/>' +
      '<circle cx="12.5" cy="13" r="1" fill="#FCF3CE"/><circle cx="19" cy="18" r="1" fill="#FCF3CE"/>' },
    'Black Olives': { c: '#2B2430', size: 22, svg:
      '<path d="M16 4a12 12 0 1 1 0 24 12 12 0 0 1 0-24Zm0 7.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z" fill="#2A232E"/>' +
      '<path d="M9 10a9.6 9.6 0 0 1 5-4" stroke="#6B5E72" stroke-width="1.8" stroke-linecap="round" fill="none" opacity=".75"/>' },
    'Green Olives': { c: '#7D8F3A', size: 22, svg:
      '<path d="M16 4a12 12 0 1 1 0 24 12 12 0 0 1 0-24Zm0 7.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z" fill="#7E9139"/>' +
      '<circle cx="16" cy="16" r="4.2" fill="#C3453A"/>' +
      '<path d="M9 10a9.6 9.6 0 0 1 5-4" stroke="#BDCB86" stroke-width="1.8" stroke-linecap="round" fill="none" opacity=".8"/>' },
    'Donair Meat': { c: '#8A5A34', size: 28, svg:
      '<path d="M3 13c5-2 8 2 13 0s10-1 13 1l-1 6c-5 2-8-2-13 0s-10 1-13-1Z" fill="#8A5A34"/>' +
      '<path d="M3 15c5-2 8 2 13 0s10-1 13 1" stroke="#B5845A" stroke-width="1.5" fill="none" opacity=".65"/>' +
      '<path d="M5 18.5c4-1.5 7 1.5 11 0" stroke="#5E3A1E" stroke-width="1.2" fill="none" opacity=".5"/>' },
    'Ham': { c: '#E29A9A', size: 26, svg:
      '<path d="M5.6 12.4c2.6-2.6 6-3.6 9.4-3.2 3.2.4 6.6-.6 9.2 1.2 2.4 1.7 3 5.4 1.2 7.8-1.8 2.4-5.2 2.4-8 3-3 .6-6.4 1.2-8.8-.8-2.4-2-4.2-5.6-3-8Z" fill="#DE9494"/>' +
      '<path d="M8 14.2c3.4.8 6.8-.8 10.2 0 2 .5 3.4.2 4.6-.8" stroke="#F5C6C6" stroke-width="1.5" fill="none" stroke-linecap="round" opacity=".85"/>' +
      '<path d="M7.6 19c3.4-1 6.8.6 10.2-.2 1.8-.4 3.2-.2 4.4.6" stroke="#F5C6C6" stroke-width="1.3" fill="none" stroke-linecap="round" opacity=".7"/>' +
      '<path d="M11 11.4c2.4.4 5 .2 7.4-.2" stroke="#C97B7B" stroke-width="1" fill="none" stroke-linecap="round" opacity=".6"/>' }
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
    var look = TOPPING_LOOK[name];
    if (!look) return;
    var n = 7;
    for (var i = 0; i < n; i++) {
      var bit = document.createElement('span');
      bit.className = 'bit';
      bit.setAttribute('data-for', name);
      // golden-angle scatter, jittered, so toppings never land in a visible ring
      var a = (i * 2.399 + Math.random() * 0.7);
      var r = 13 + Math.sqrt((i + 0.55) / n) * 31;
      bit.style.left = (50 + Math.cos(a) * r) + '%';
      bit.style.top = (50 + Math.sin(a) * r) + '%';
      var size = look.size * (0.86 + Math.random() * 0.28);
      bit.style.setProperty('--w', size.toFixed(1) + 'px');
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
