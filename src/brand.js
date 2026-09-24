/* Tasty Pizza — ordering behaviour.

   Categories -> items -> cart -> checkout. No framework: page speed is a
   conversion lever on a takeaway site, and the whole of this is smaller than
   the smallest animation library.

   Everything the customer builds is kept in localStorage, so closing the tab
   by accident does not throw the order away. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var money = function (n) { return '$' + (Math.round(n * 100) / 100).toFixed(2); };
  var esc = function (s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };

  var CFG = window.SHOP || {};

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

  /* ------------------------------------------------------------ open / closed */
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
    var hours = CFG.hours || [];
    if (!hours.length) return;
    var now = halifaxNow(), idx = DAYS.indexOf(now.day), by = {};
    hours.forEach(function (h) { by[h.day] = h; });
    var prev = by[DAYS[(idx + 6) % 7]], today = by[now.day], txt, shut = true;

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

  /* ------------------------------------------------------------ nav sheet */
  var dots = $('[data-sheet-toggle]'), sheet = $('[data-sheet]');
  if (dots && sheet) {
    dots.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var open = sheet.hasAttribute('data-open');
      if (open) sheet.removeAttribute('data-open'); else sheet.setAttribute('data-open', '');
      dots.setAttribute('aria-expanded', String(!open));
    });
    sheet.addEventListener('click', function (ev) { if (ev.target.closest('a')) close(); });
    document.addEventListener('click', function (ev) {
      if (!sheet.contains(ev.target) && !dots.contains(ev.target)) close();
    });
    function close() { sheet.removeAttribute('data-open'); dots.setAttribute('aria-expanded', 'false'); }
  }

  /* ------------------------------------------------------------ the cart */
  var KEY = 'tp.cart.v1';
  var cart = [];
  try { cart = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { cart = []; }
  if (!Array.isArray(cart)) cart = [];

  function save() { try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (e) {} }
  function count() { return cart.reduce(function (s, r) { return s + r.qty; }, 0); }
  function subtotal() { return cart.reduce(function (s, r) { return s + r.price * r.qty; }, 0); }

  function add(name, price, note) {
    var hit = null;
    cart.forEach(function (r) { if (r.name === name && r.note === note && r.price === price) hit = r; });
    if (hit) hit.qty += 1; else cart.push({ name: name, note: note || '', price: price, qty: 1 });
    save();
    paintCart();
    var btn = $('[data-cart-open]');
    if (btn) { btn.setAttribute('data-bump', ''); setTimeout(function () { btn.removeAttribute('data-bump'); }, 440); }
  }

  function setQty(i, q) {
    if (q <= 0) cart.splice(i, 1); else cart[i].qty = q;
    save();
    paintCart();
  }

  function totals() {
    var sub = subtotal();
    var tax = sub * (CFG.taxRate || 0.14);
    return { sub: sub, tax: tax, total: sub + tax };
  }

  function paintCart() {
    var n = count();
    var btn = $('[data-cart-open]');
    if (btn) {
      btn.hidden = n === 0;
      var b = btn.querySelector('b');
      if (b) b.textContent = n;
      btn.setAttribute('aria-label', n + (n === 1 ? ' item' : ' items') + ' in your order');
    }
    var list = $('[data-cart-list]');
    if (!list) return;
    if (!cart.length) {
      list.innerHTML = '<div class="cart-empty"><p>Nothing here yet.</p>'
        + '<button class="btn btn-line btn-sm" type="button" data-cart-close>Browse the menu</button></div>';
    } else {
      list.innerHTML = cart.map(function (r, i) {
        return '<div class="cart-row">'
          + '<div class="qty"><button type="button" data-q="' + i + '" data-d="-1" aria-label="One fewer">&minus;</button>'
          + '<span>' + r.qty + '</span>'
          + '<button type="button" data-q="' + i + '" data-d="1" aria-label="One more">+</button></div>'
          + '<span class="n">' + esc(r.name) + (r.note ? '<small>' + esc(r.note) + '</small>' : '') + '</span>'
          + '<span class="p">' + money(r.price * r.qty) + '</span></div>';
      }).join('');
    }
    var t = totals();
    var f = $('[data-cart-foot]');
    if (f) f.hidden = !cart.length;
    var set = function (sel, v) { var el = $(sel); if (el) el.textContent = v; };
    set('[data-sub]', money(t.sub));
    set('[data-tax]', money(t.tax));
    set('[data-total]', money(t.total));
    set('[data-taxlabel]', 'HST ' + Math.round((CFG.taxRate || 0.14) * 100) + '%');
  }

  function openCart(on) {
    var c = $('[data-cart]'), s = $('[data-scrim]');
    if (!c) return;
    if (on) { c.setAttribute('data-open', ''); s.setAttribute('data-open', ''); }
    else { c.removeAttribute('data-open'); s.removeAttribute('data-open'); showPay(false); }
    document.body.style.overflow = on ? 'hidden' : '';
  }

  function showPay(on) {
    var pay = $('[data-pay]'), list = $('[data-cart-list]'), cta = $('[data-checkout]');
    if (!pay) return;
    pay.hidden = !on;
    if (list) list.hidden = on;
    if (cta) cta.hidden = on;
  }

  /* ------------------------------------------------------------ categories */
  var grid = $('[data-cats]'), view = $('[data-catview]');

  function openCategory(id) {
    if (!view) return;
    var data = (CFG.categories || []).filter(function (c) { return c.id === id; })[0];
    if (!data) return;
    view.innerHTML = render(data);
    view.hidden = false;
    if (grid) grid.hidden = true;
    var head = $('[data-order-head]');
    if (head) head.hidden = true;
    if (history.replaceState) history.replaceState(null, '', '#c-' + id);
    var anchor = $('#order');
    if (anchor) anchor.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
  }

  function closeCategory() {
    if (!view) return;
    view.hidden = true;
    view.innerHTML = '';
    if (grid) grid.hidden = false;
    var head = $('[data-order-head]');
    if (head) head.hidden = false;
    if (history.replaceState) history.replaceState(null, '', '#order');
  }

  function itemRow(it, extra) {
    var media = it.photo
      ? '<div class="item-media"><img src="' + CFG.img + it.photo + '@sm.webp" width="400" height="300"'
        + ' loading="lazy" alt="' + esc(it.alt || it.name) + '"></div>' : '';
    var tags = (it.tags || []).map(function (t) {
      if (t === 'veg') return '<span class="tag tag-veg">Veg</span>';
      return '';
    }).join('');
    var side;
    if (it.sizes && it.sizes.length > 1) {
      // picking a size IS adding it — one tap, no modal
      side = '<div class="sizes">' + it.sizes.map(function (s) {
        return s.price == null ? '' :
          '<button class="sizebtn" type="button" data-add="' + esc(it.name) + '"'
          + ' data-price="' + s.price + '" data-note="' + esc(s.label) + '">'
          + '<i>' + esc(s.label) + '</i><b>' + money(s.price) + '</b></button>';
      }).join('') + '</div>';
    } else {
      var p = it.sizes && it.sizes[0] ? it.sizes[0].price : null;
      side = p == null
        ? '<span class="price"><small>Ask</small></span>'
        : '<span class="price">' + money(p) + '</span>'
          + '<button class="add" type="button" data-add="' + esc(it.name) + '"'
          + ' data-price="' + p + '">Add</button>';
    }
    return '<li class="item' + (extra ? ' ' + extra : '') + '">' + media
      + '<div class="item-body"><h4>' + esc(it.name) + tags + '</h4>'
      + (it.desc ? '<p>' + esc(it.desc) + '</p>' : '') + '</div>'
      + '<div class="item-side">' + side + '</div></li>';
  }

  function offerRow(d) {
    var was = d.compareAt && d.compareAt > d.price
      ? '<span class="was">' + money(d.compareAt) + '</span>' : '';
    return '<li class="item offer">'
      + (d.photo ? '<div class="item-media"><img src="' + CFG.img + d.photo + '@sm.webp" width="400"'
        + ' height="300" loading="lazy" alt=""></div>' : '')
      + '<div class="item-body"><h4>' + esc(d.name) + '<span class="flag">Deal</span></h4>'
      + '<p>' + esc(d.desc || '') + '</p></div>'
      + '<div class="item-side"><span class="price">' + was + money(d.price) + '</span>'
      + '<button class="add" type="button" data-add="' + esc(d.name) + '" data-price="' + d.price
      + '" data-note="deal">Add</button></div></li>';
  }

  function render(c) {
    var html = '<div class="catview-head">'
      + '<button class="back" type="button" data-back>&larr; All categories</button>'
      + '<h2>' + esc(c.name) + '</h2></div>'
      + (c.blurb ? '<p class="catview-blurb">' + esc(c.blurb) + '</p>' : '');

    // offers first — that is the whole point of an offer
    var offers = (CFG.deals || []).filter(function (d) { return (d.cats || []).indexOf(c.id) >= 0; });
    if (offers.length) {
      html += '<h3 class="grouphead">Deals on these</h3><ul class="items">'
        + offers.map(offerRow).join('') + '</ul>';
    }
    // then the ones people actually order
    var pop = [];
    c.groups.forEach(function (g) {
      g.items.forEach(function (it) { if ((it.tags || []).indexOf('popular') >= 0) pop.push(it); });
    });
    if (pop.length) {
      html += '<h3 class="grouphead">Most ordered</h3><ul class="items">'
        + pop.map(function (it) { return itemRow(it); }).join('') + '</ul>';
    }
    // then everything, in the shop's own groupings
    c.groups.forEach(function (g) {
      if (!g.items.length) return;
      html += '<h3 class="grouphead">' + esc(g.name) + '</h3>'
        + (g.note ? '<p class="groupnote">' + esc(g.note) + '</p>' : '')
        + '<ul class="items">' + g.items.map(function (it) { return itemRow(it); }).join('') + '</ul>';
    });
    return html;
  }

  /* ------------------------------------------------------------ one click handler */
  document.addEventListener('click', function (ev) {
    var t = ev.target;

    var cat = t.closest('[data-cat]');
    if (cat) { ev.preventDefault(); openCategory(cat.getAttribute('data-cat')); return; }
    if (t.closest('[data-back]')) { closeCategory(); return; }

    var addBtn = t.closest('[data-add]');
    if (addBtn) {
      var price = parseFloat(addBtn.getAttribute('data-price'));
      if (isNaN(price)) return;
      var name = addBtn.getAttribute('data-add');
      var note = addBtn.getAttribute('data-note') || '';
      if (name === 'Custom pizza') { var b = buildState(); name = b.name; note = b.note; price = b.price; }
      add(name, price, note);
      addBtn.setAttribute('data-done', '');
      var was = addBtn.innerHTML;
      if (addBtn.classList.contains('add')) addBtn.textContent = 'Added';
      setTimeout(function () { addBtn.removeAttribute('data-done'); addBtn.innerHTML = was; }, 1100);
      return;
    }

    if (t.closest('[data-cart-open]')) { openCart(true); return; }
    if (t.closest('[data-cart-close]') || t.closest('[data-scrim]')) { openCart(false); return; }
    if (t.closest('[data-checkout]')) { showPay(true); return; }
    if (t.closest('[data-paydone]')) { showPay(false); return; }

    var q = t.closest('[data-q]');
    if (q) {
      var i = parseInt(q.getAttribute('data-q'), 10);
      setQty(i, cart[i].qty + parseInt(q.getAttribute('data-d'), 10));
    }
  });

  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') openCart(false); });

  /* ------------------------------------------------------------ the builder */
  var B = { size: 1, crust: 'White', sur: 0, tops: [] };
  var BD = window.BUILD;

  function buildState() {
    var n = Math.min(B.tops.length, BD.prices.length - 1);
    var price = BD.prices[n][B.size] + (B.sur || 0);
    var label = !B.tops.length ? 'just cheese'
      : (B.tops.length >= BD.max ? BD.special : B.tops.join(', '));
    return { price: price, name: BD.sizes[B.size] + ' pizza',
      note: label + (B.crust !== 'White' ? ' · ' + B.crust : ''),
      short: BD.sizes[B.size] + ' · '
        + (!B.tops.length ? 'just cheese'
          : (B.tops.length >= BD.max ? BD.special : B.tops.length + ' topping'
            + (B.tops.length > 1 ? 's' : ''))) };
  }

  function paintBuild(bump) {
    if (!BD) return;
    var st = buildState();
    var p = $('[data-price]');
    if (p) {
      p.textContent = money(st.price);
      if (bump) { p.setAttribute('data-bump', ''); setTimeout(function () { p.removeAttribute('data-bump'); }, 320); }
    }
    var note = $('[data-note]');
    if (note) note.textContent = st.short;
    var c = $('[data-count]');
    if (c) c.textContent = B.tops.length + ' of ' + BD.max;
    var dough = $('[data-dough]');
    if (dough) {
      if (B.tops.length) dough.setAttribute('data-topped', ''); else dough.removeAttribute('data-topped');
      dough.style.width = [78, 86, 94, 100][B.size] + '%';
    }
    $$('.topbtn').forEach(function (btn) {
      var on = B.tops.indexOf(btn.getAttribute('data-top')) >= 0;
      btn.setAttribute('aria-pressed', String(on));
      if (!on && B.tops.length >= BD.max) btn.setAttribute('data-full', '');
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
      var ang = i * 2.399 + Math.random() * 0.7, rad = 13 + Math.sqrt((i + 0.55) / 7) * 31;
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
    var grid2 = $('[data-topgrid]');
    if (!grid2 || !BD) return;
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
        paintBuild(true);
      });
    });
    $$('[data-crusts] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        B.crust = b.getAttribute('data-crust');
        B.sur = parseFloat(b.getAttribute('data-sur')) || 0;
        $$('[data-crusts] .chip').forEach(function (o) {
          if (o === b) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
        });
        paintBuild(true);
      });
    });
    grid2.addEventListener('click', function (ev) {
      var b = ev.target.closest('.topbtn');
      if (!b) return;
      var name = b.getAttribute('data-top'), at = B.tops.indexOf(name);
      if (at >= 0) { B.tops.splice(at, 1); unsprinkle(name); }
      else { if (B.tops.length >= BD.max) return; B.tops.push(name); sprinkle(name); }
      paintBuild(true);
    });
    paintBuild(false);
  }

  /* ------------------------------------------------------------ go */
  paintClock();
  setInterval(paintClock, 60000);
  paintCart();
  initBuilder();
  if (location.hash.indexOf('#c-') === 0) openCategory(location.hash.slice(3));
})();
