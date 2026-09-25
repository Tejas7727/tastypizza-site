/* Tasty Pizza — ordering behaviour.

   Categories -> items -> cart -> checkout. No framework: page speed is a
   conversion lever on a takeaway site, and the whole of this is smaller than
   the smallest animation library.

   Two ideas hold the funnel together:

   * Nothing opens in a modal. A pizza row expands where it sits, a deal expands
     into its slots, a slot expands into the builder. You can always see where
     you came from, so there is never a moment of "how do I get back".
   * The category rail never leaves. Once you are inside Seafood you are one tap
     from Pizza, all the way down the list, without hunting for a back button.

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
  var BD = window.BUILD;

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
    sheet.addEventListener('click', function (ev) { if (ev.target.closest('a')) closeSheet(); });
    document.addEventListener('click', function (ev) {
      if (!sheet.contains(ev.target) && !dots.contains(ev.target)) closeSheet();
    });
  }
  function closeSheet() {
    if (!sheet) return;
    sheet.removeAttribute('data-open');
    dots.setAttribute('aria-expanded', 'false');
  }

  /* ------------------------------------------------------------ the cart */
  var KEY = 'tp.cart.v1', NKEY = 'tp.note.v1';
  var cart = [];
  try { cart = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { cart = []; }
  if (!Array.isArray(cart)) cart = [];
  var orderNote = '';
  try { orderNote = localStorage.getItem(NKEY) || ''; } catch (e) { orderNote = ''; }

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
    var pay = $('[data-pay]'), list = $('[data-cart-list]'), cta = $('[data-checkout]'),
        nf = $('[data-notefield]');
    if (!pay) return;
    pay.hidden = !on;
    if (list) list.hidden = on;
    if (cta) cta.hidden = on;
    if (nf) nf.hidden = on;
    var box = $('[data-paynote]'), txt = $('[data-paynote-text]');
    if (box) {
      box.hidden = !on || !orderNote;
      if (txt) txt.textContent = orderNote;
    }
  }

  var noteEl = $('[data-order-note]');
  if (noteEl) {
    noteEl.value = orderNote;
    noteEl.addEventListener('input', function () {
      orderNote = noteEl.value.slice(0, 280);
      try { localStorage.setItem(NKEY, orderNote); } catch (e) {}
    });
  }

  /* ------------------------------------------------------------ expanding panels

     One mechanism for three jobs: a pizza row, a deal, a slot inside a deal.
     The 0fr -> 1fr grid trick animates to the content's own height without
     anyone having to measure anything. */
  var panelSeq = 0;

  function togglePanel(host, fill) {
    var open = host.hasAttribute('data-open');
    if (open) { host.removeAttribute('data-open'); host.removeAttribute('data-grown'); return false; }
    // only one row open at a time inside the same list — two open accordions
    // is where a simple page starts feeling like a form
    var sibs = host.parentNode ? host.parentNode.children : [];
    Array.prototype.slice.call(sibs).forEach(function (s) {
      if (s !== host && s.hasAttribute && s.hasAttribute('data-open')) {
        s.removeAttribute('data-open');
        s.removeAttribute('data-grown');
      }
    });
    var body = host.querySelector(':scope > .panel > .panel-in');
    if (body && !body.getAttribute('data-filled')) {
      body.setAttribute('data-filled', '1');
      fill(body);
    }
    host.setAttribute('data-open', '');
    // the 0fr -> 1fr height animation needs overflow:hidden, which also kills
    // position:sticky on the pizza inside. Once the panel has finished growing
    // the clipping has no more work to do, so it comes off and the pizza can
    // follow you down the toppings list on a phone.
    setTimeout(function () { if (host.hasAttribute('data-open')) host.setAttribute('data-grown', ''); }, 460);
    // a panel that opens below the fold is a panel nobody knows opened
    setTimeout(function () {
      var r = host.getBoundingClientRect();
      var bar = parseFloat(getComputedStyle(document.documentElement)
        .getPropertyValue('--bar')) || 60;
      if (r.top < bar + 8 || r.top > window.innerHeight * 0.55) {
        window.scrollTo({ top: window.scrollY + r.top - bar - 70,
          behavior: calm ? 'auto' : 'smooth' });
      }
    }, 90);
    return true;
  }

  function mountBuilder(body, opts, onAdd) {
    var cfg = new window.PizzaConfig(opts);
    body.innerHTML = cfg.render();
    cfg.mount(body, onAdd);
    return cfg;
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
    // put the category you are in where you can see it on the rail
    var on = $('.railbtn[data-on]', view);
    if (on && on.parentNode) {
      on.parentNode.scrollTo({ left: on.offsetLeft - 16, behavior: calm ? 'auto' : 'smooth' });
    }
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

  function tagsOf(it) {
    return (it.tags || []).map(function (t) {
      return t === 'veg' ? '<span class="tag tag-veg">Veg</span>' : '';
    }).join('');
  }

  function media(photo, alt, cls) {
    if (!photo) return '';
    return '<div class="item-media' + (cls ? ' ' + cls : '') + '">'
      + '<img src="' + CFG.img + photo + '@sm.webp" width="400" height="300" loading="lazy"'
      + ' alt="' + esc(alt || '') + '"></div>';
  }

  /* a row that opens the configurator rather than carrying a price */
  function builderRow(it) {
    var from = BD ? Math.min.apply(null, BD.prices[0]) : 0;
    return '<li class="item item-x is-build" data-x="build">'
      + '<button class="item-hit" type="button" data-x-toggle aria-expanded="false">'
      + media(it.photo, it.alt || it.name)
      + '<span class="item-body"><span class="h4">' + esc(it.name)
      + '<span class="flag flag-build">Make it yours</span></span>'
      + (it.desc ? '<span class="p">' + esc(it.desc) + '</span>' : '') + '</span>'
      + '<span class="item-side"><span class="price"><small>from</small>' + money(from) + '</span>'
      + '<span class="add add-ghost">Build it</span></span>'
      + '</button>'
      + '<div class="panel"><div class="panel-in"></div></div></li>';
  }

  function itemRow(it, extra) {
    if (it.builder) return builderRow(it);
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
    return '<li class="item' + (extra ? ' ' + extra : '') + '">'
      + media(it.photo, it.alt || it.name)
      + '<div class="item-body"><h4>' + esc(it.name) + tagsOf(it) + '</h4>'
      + (it.desc ? '<p>' + esc(it.desc) + '</p>' : '') + '</div>'
      + '<div class="item-side">' + side + '</div></li>';
  }

  function offerRow(d) {
    var was = d.compareAt && d.compareAt > d.price
      ? '<span class="was">' + money(d.compareAt) + '</span>' : '';
    var slots = d.slots || [];
    if (!slots.length) {
      return '<li class="item offer">'
        + media(d.photo, '')
        + '<div class="item-body"><h4>' + esc(d.name) + '<span class="flag">Deal</span></h4>'
        + '<p>' + esc(d.desc || '') + '</p></div>'
        + '<div class="item-side"><span class="price">' + was + money(d.price) + '</span>'
        + '<button class="add" type="button" data-add="' + esc(d.name) + '" data-price="' + d.price
        + '" data-note="deal">Add</button></div></li>';
    }
    // a deal you have to build: it opens into its slots
    var n = slots.filter(function (s) { return s.type === 'pizza'; }).length;
    return '<li class="item item-x offer" data-x="deal" data-deal="' + esc(d.id) + '">'
      + '<button class="item-hit" type="button" data-x-toggle aria-expanded="false">'
      + media(d.photo, '')
      + '<span class="item-body"><span class="h4">' + esc(d.name) + '<span class="flag">Deal</span></span>'
      + '<span class="p">' + esc(d.desc || '') + '</span></span>'
      + '<span class="item-side"><span class="price">' + was + money(d.price) + '</span>'
      + '<span class="add add-ghost">' + (n > 1 ? 'Pick ' + n + ' pizzas' : 'Pick toppings') + '</span>'
      + '</span></button>'
      + '<div class="panel"><div class="panel-in"></div></div></li>';
  }

  function dealPanel(body, d) {
    var slots = d.slots || [];
    var cfgs = {};
    body.innerHTML = '<div class="slots">'
      + slots.map(function (s, i) {
        if (s.type !== 'pizza') {
          return '<div class="slot slot-fixed"><b>' + esc(s.label) + '</b>'
            + '<span>Included</span></div>';
        }
        return '<div class="slot" data-slot="' + i + '">'
          + '<button class="slot-hit" type="button" data-x-toggle aria-expanded="false">'
          + '<b>' + esc(s.label) + '</b>'
          + '<span data-slot-sum>' + (s.included ? s.included + ' toppings included'
              + ' · tap to choose' : 'Tap to choose toppings') + '</span>'
          + '<i class="chev" aria-hidden="true"></i></button>'
          + '<div class="panel"><div class="panel-in"></div></div></div>';
      }).join('')
      + '</div>'
      + '<div class="slots-foot"><p class="slots-note" data-deal-extra hidden></p>'
      + '<button class="btn btn-red btn-wide" type="button" data-deal-add>'
      + 'Add the deal · ' + money(d.price) + '</button></div>';

    function extras() {
      var x = 0;
      Object.keys(cfgs).forEach(function (k) { x += cfgs[k].price(); });
      return x;
    }
    function repaint() {
      var x = extras();
      var btn = body.querySelector('[data-deal-add]');
      if (btn) btn.textContent = 'Add the deal · ' + money(d.price + x);
      var note = body.querySelector('[data-deal-extra]');
      if (note) {
        note.hidden = x <= 0;
        note.textContent = x > 0 ? money(x) + ' of extra toppings on top of the deal price.' : '';
      }
    }

    body.addEventListener('click', function (ev) {
      var hit = ev.target.closest('[data-x-toggle]');
      var slot = hit && hit.closest('[data-slot]');
      if (slot && body.contains(slot)) {
        var i = parseInt(slot.getAttribute('data-slot'), 10);
        var s = slots[i];
        var opened = togglePanel(slot, function (inner) {
          cfgs[i] = mountBuilder(inner, { size: s.size, included: s.included,
            dealPrice: d.price }, function () {
            slot.removeAttribute('data-open');
            hit.setAttribute('aria-expanded', 'false');
            var sum = slot.querySelector('[data-slot-sum]');
            if (sum) {
              var c = cfgs[i];
              sum.textContent = BD.sizes[c.size] + ' · ' + c.label()
                + (c.price() > 0 ? ' · +' + money(c.price()) : '');
            }
            slot.setAttribute('data-set', '');
            repaint();
          });
          cfgs[i].onChange = repaint;
        });
        hit.setAttribute('aria-expanded', String(opened));
        return;
      }
      if (ev.target.closest('[data-deal-add]')) {
        var parts = slots.map(function (s, i) {
          if (s.type !== 'pizza') return s.label;
          var c = cfgs[i];
          return s.label.replace(/^Your |^Pizza \d+ — /, '') + ': '
            + (c ? c.label() : 'just cheese');
        });
        add(d.name, d.price + extras(), parts.join(' · '));
        openCart(true);
      }
    });
    repaint();
  }

  function rail(active) {
    var cats = CFG.categories || [];
    return '<div class="rail" data-rail>'
      + '<button class="rail-back" type="button" data-back aria-label="All categories">'
      + '<i class="chev-l" aria-hidden="true"></i></button>'
      + '<div class="rail-scroll">'
      + cats.map(function (c) {
        return '<button class="railbtn" type="button" data-cat="' + esc(c.id) + '"'
          + (c.id === active ? ' data-on aria-current="true"' : '') + '>'
          + esc(c.name) + '</button>';
      }).join('')
      + '</div></div>';
  }

  function render(c) {
    var html = rail(c.id)
      + '<div class="catview-head"><h2>' + esc(c.name) + '</h2></div>'
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

    // an expanding row. Deal slots are handled by their own panel's listener.
    var toggle = t.closest('[data-x-toggle]');
    if (toggle) {
      // a slot toggle lives inside a deal's panel and is that panel's business.
      // Without this it would walk up to the deal row and shut the whole thing.
      if (toggle.closest('.panel-in')) return;
      var host = toggle.closest('[data-x]');
      if (host) {
        ev.preventDefault();
        var kind = host.getAttribute('data-x');
        var opened = togglePanel(host, function (body) {
          if (kind === 'deal') {
            var id = host.getAttribute('data-deal');
            var d = (CFG.deals || []).filter(function (x) { return x.id === id; })[0];
            if (d) dealPanel(body, d);
          } else {
            mountBuilder(body, {}, function (cfg) {
              add(cfg.name(), cfg.price(), cfg.label()
                + (cfg.crust !== 'White' ? ' · ' + cfg.crust + ' crust' : ''));
              host.removeAttribute('data-open');
              toggle.setAttribute('aria-expanded', 'false');
              openCart(true);
            });
          }
        });
        toggle.setAttribute('aria-expanded', String(opened));
      }
      return;
    }

    var cat = t.closest('[data-cat]');
    if (cat) { ev.preventDefault(); openCategory(cat.getAttribute('data-cat')); return; }
    if (t.closest('[data-back]')) { closeCategory(); return; }

    var addBtn = t.closest('[data-add]');
    if (addBtn) {
      var price = parseFloat(addBtn.getAttribute('data-price'));
      if (isNaN(price)) return;
      add(addBtn.getAttribute('data-add'), price, addBtn.getAttribute('data-note') || '');
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

  /* ------------------------------------------------------------ the hero board

     A wooden board that stays put, and pizzas that slide across it right to
     left. The pies are cut out with an alpha edge, so what moves is the pizza
     itself and not a disc of white. */
  (function () {
    var S = window.SLIDES || [];
    var stage = $('[data-wheelstage]');
    if (!stage || S.length < 2) return;

    var discs = $$('.disc', stage), ticks = $('[data-ticks]'), dealEl = $('[data-deal]');
    var badge = $('[data-badge]');
    var HOLD = 2000;
    var cur = 0, timer = null, busy = false;

    S.forEach(function (s, i) {
      var t = document.createElement('button');
      t.type = 'button';
      t.setAttribute('role', 'tab');
      t.setAttribute('aria-label', s.name);
      t.addEventListener('click', function () {
        if (i === cur) return;
        stop(); go(i, i > cur ? 1 : -1); start();
      });
      if (ticks) ticks.appendChild(t);
    });

    function paint() {
      var s = S[cur];
      var k = $('[data-kicker]', dealEl);
      if (k) { k.textContent = s.kick; k.className = 'kicker ' + (s.cls || ''); }
      var name = $('[data-dealname]', dealEl);
      if (name) {
        // the builder slide is a door, so it gets a link rather than a label
        name.innerHTML = s.build
          ? '<a href="#build" data-build-jump>' + esc(s.name) + '</a>'
          : esc(s.name);
      }
      var desc = $('[data-dealdesc]', dealEl);
      if (desc) desc.textContent = s.desc || '';
      var was = $('[data-dealwas]', dealEl), save = $('[data-dealsave]', dealEl);
      if (was && save) {
        was.hidden = !s.was;
        save.hidden = false;
        if (s.was) {
          was.textContent = money(s.was);
          save.textContent = 'Save ' + money(s.was - s.price);
          save.className = 'save';
        } else {
          save.textContent = (s.unit ? s.unit + ' · ' : '')
            + (s.build ? 'from ' : '') + money(s.price);
          save.className = 'unit';
        }
      }
      if (badge) {
        badge.querySelector('[data-badge-kick]').textContent =
          s.was ? 'Deal' : (s.build ? 'Build' : 'From');
        badge.querySelector('[data-badge-price]').textContent = money(s.price);
        badge.querySelector('[data-badge-was]').textContent = s.was ? money(s.was) : '';
        badge.setAttribute('data-pop', '');
      }
      if (dealEl) dealEl.setAttribute('data-flash', '');
      requestAnimationFrame(function () {
        if (dealEl) dealEl.removeAttribute('data-flash');
        if (badge) badge.removeAttribute('data-pop');
      });
      if (ticks) {
        $$('button', ticks).forEach(function (t, i) {
          t.removeAttribute('data-on'); t.removeAttribute('data-run');
          t.setAttribute('aria-selected', String(i === cur));
          if (i !== cur) return;
          if (timer && !calm) { void t.offsetWidth; t.setAttribute('data-run', ''); }
          else t.setAttribute('data-on', '');
        });
      }
    }

    function go(next, dir) {
      next = (next + S.length) % S.length;
      if (busy || next === cur) return;
      busy = true;
      var from = discs[cur], to = discs[next], d = dir > 0 ? 'next' : 'prev';

      // park the incoming pie off the right of the board with no transition,
      // then release it in the same frame the outgoing one leaves
      to.classList.add('is-drag', 'in-' + d);
      to.classList.remove('is-cur');
      void to.offsetWidth;
      to.classList.remove('is-drag');

      requestAnimationFrame(function () {
        from.classList.remove('is-cur');
        from.classList.add('out-' + d);
        to.classList.remove('in-' + d);
        to.classList.add('is-cur');
      });
      setTimeout(function () {
        from.classList.remove('out-next', 'out-prev');
        from.style.transform = '';
        busy = false;
      }, 780);

      cur = next;
      paint();
    }

    function start() { stop(); if (!calm) { timer = setInterval(function () { go(cur + 1, 1); }, HOLD); paint(); } }
    function stop() { clearInterval(timer); timer = null; }

    /* drag: the pizza follows your finger off the board */
    var x0 = null, dx = 0, w = 1;
    stage.addEventListener('pointerdown', function (ev) {
      if (busy || ev.target.closest('a')) return;
      x0 = ev.clientX; dx = 0;
      w = stage.getBoundingClientRect().width || 1;
      stage.classList.add('is-drag');
      stage.setPointerCapture(ev.pointerId);
      stop();
    });
    stage.addEventListener('pointermove', function (ev) {
      if (x0 === null) return;
      dx = ev.clientX - x0;
      var f = dx / w;
      discs[cur].style.transform = 'translateX(' + (f * 100) + '%) rotate(' + (f * 11)
        + 'deg) scale(' + (1 - Math.min(Math.abs(f), .4) * .28) + ')';
    });
    function release() {
      if (x0 === null) return;
      var moved = dx;
      x0 = null; dx = 0;
      stage.classList.remove('is-drag');
      discs[cur].style.transform = '';
      if (Math.abs(moved) > 40) go(cur + (moved < 0 ? 1 : -1), moved < 0 ? 1 : -1);
      start();
    }
    stage.addEventListener('pointerup', release);
    stage.addEventListener('pointercancel', release);
    stage.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight') { stop(); go(cur + 1, 1); start(); }
      if (ev.key === 'ArrowLeft') { stop(); go(cur - 1, -1); start(); }
    });
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });

    start(); paint();
  })();

  /* ------------------------------------------------------------ go */
  paintClock();
  setInterval(paintClock, 60000);
  paintCart();

  var mount = $('[data-build-mount]');
  if (mount && window.PizzaConfig && BD) {
    mountBuilder(mount, {}, function (cfg) {
      add(cfg.name(), cfg.price(), cfg.label()
        + (cfg.crust !== 'White' ? ' · ' + cfg.crust + ' crust' : ''));
      openCart(true);
    });
  }

  if (location.hash.indexOf('#c-') === 0) openCategory(location.hash.slice(3));
})();
