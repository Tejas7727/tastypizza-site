/* Tasty Pizza — behaviour for every page.

   Each page is a real page, so the browser does the hard parts: Back returns
   to exactly where you were on the page you left, and a link is a link. This
   file only adds what a static page cannot do on its own:

     every page   the open/closed pill, the phone menu, the order count, "Added"
     home         the pizza wheel
     categories   size, quantity and Add on each card
     build        the pizza builder (build your own, customize, fill a deal)
     order        the order itself

   The order lives in localStorage, so closing the tab does not lose it. */
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
  var PAGE = document.body.getAttribute('data-page');
  var R = document.body.getAttribute('data-root') || '';
  var SHOP = window.SHOP || {};

  /* ------------------------------------------------------------ smooth wheel */
  if (!calm && typeof Lenis !== 'undefined') {
    window.__lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 0.95, anchors: true,
      autoRaf: true, autoToggle: true });
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
    var hours = SHOP.hours || [];
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

  /* ------------------------------------------------------------ phone menu */
  var dots = $('[data-sheet-toggle]'), sheet = $('[data-sheet]');
  function closeSheet() {
    if (!sheet) return;
    sheet.removeAttribute('data-open');
    dots.setAttribute('aria-expanded', 'false');
  }
  if (dots && sheet) {
    dots.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var open = sheet.hasAttribute('data-open');
      if (open) sheet.removeAttribute('data-open'); else sheet.setAttribute('data-open', '');
      dots.setAttribute('aria-expanded', String(!open));
    });
    document.addEventListener('click', function (ev) {
      if (!sheet.contains(ev.target) && !dots.contains(ev.target)) closeSheet();
    });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeSheet(); });
  }

  /* ------------------------------------------------------------ the order */
  var KEY = 'tp.cart.v1', NKEY = 'tp.note.v1';
  function load() {
    try {
      var c = JSON.parse(localStorage.getItem(KEY) || '[]');
      return Array.isArray(c) ? c : [];
    } catch (e) { return []; }
  }
  var cart = load();
  function save() { try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (e) {} }
  function count() { return cart.reduce(function (s, r) { return s + r.qty; }, 0); }

  function add(name, price, note, qty) {
    var hit = null;
    cart.forEach(function (r) { if (r.name === name && r.note === (note || '') && r.price === price) hit = r; });
    if (hit) hit.qty += qty; else cart.push({ name: name, note: note || '', price: price, qty: qty });
    save();
    paintCount(true);
  }

  function paintCount(bump) {
    var n = count();
    $$('[data-count]').forEach(function (b) { b.textContent = n; b.hidden = n === 0; });
    var btn = $('[data-cartbtn]');
    if (btn) {
      btn.setAttribute('aria-label', n ? 'Your order, ' + n + ' item' + (n === 1 ? '' : 's') : 'Your order');
      if (PAGE === 'order') btn.setAttribute('aria-current', 'page');
      if (bump && !calm) {
        btn.removeAttribute('data-bump'); void btn.offsetWidth; btn.setAttribute('data-bump', '');
      }
    }
  }

  /* ------------------------------------------------------------ "Added" */
  var toastEl = $('[data-toast]'), toastT;
  function toast(msg) {
    if (!toastEl) return;
    clearTimeout(toastT);
    toastEl.removeAttribute('data-out');
    toastEl.innerHTML = '<span>' + esc(msg) + '</span>'
      + (PAGE === 'order' ? '' : '<a href="' + R + 'order.html">View order</a>');
    toastEl.hidden = false;
    toastT = setTimeout(function () {
      toastEl.setAttribute('data-out', '');
      toastT = setTimeout(function () { toastEl.hidden = true; }, 260);
    }, 3600);
  }
  function addedText(qty, name, note) {
    return 'Added ' + (qty > 1 ? qty + ' × ' : '') + name + (note && note !== 'deal' ? ' · ' + note : '');
  }

  /* Back, when it means "where I was": the browser returns the previous page
     at the spot it was left. With no page of ours behind (a shared link, a
     fresh tab) the link simply goes where its href says. */
  function cameFromHere() {
    try { return document.referrer && new URL(document.referrer).origin === location.origin; }
    catch (e) { return false; }
  }
  $$('[data-back]').forEach(function (a) {
    a.addEventListener('click', function (ev) {
      if (cameFromHere() && history.length > 1) { ev.preventDefault(); history.back(); }
    });
  });

  /* A page restored from the back-forward cache keeps its old count, and a
     builder that sent us back leaves its "Added" message here to be shown. */
  addEventListener('pageshow', function (ev) {
    if (ev.persisted) { cart = load(); paintCount(false); if (PAGE === 'order') paintOrder(); }
    var msg = null;
    try { msg = sessionStorage.getItem('tp.toast'); sessionStorage.removeItem('tp.toast'); } catch (e) {}
    if (msg) { paintCount(true); toast(msg); }
  });

  /* ------------------------------------------------------------ dish cards */
  function qtyOf(card) { return parseInt($('[data-qty]', card).textContent, 10) || 1; }
  function paintCard(card) {
    var addBtn = $('[data-add]', card);
    if (!addBtn) return;
    var picked = $('[data-szpick] [aria-selected="true"]', card);
    var size = picked ? parseInt(picked.getAttribute('data-i'), 10) : 0;
    var base = picked ? parseFloat(picked.getAttribute('data-price')) : parseFloat(addBtn.getAttribute('data-base'));
    var extra = 0, withs = [];
    // tick boxes (cheese, extra meat) are priced for the size picked
    $$('[data-addon]', card).forEach(function (box) {
      var p = JSON.parse(box.getAttribute('data-prices'))[size];
      box.parentNode.querySelector('[data-addon-price]').textContent = money(p);
      if (box.checked) { extra += p; withs.push(box.getAttribute('data-addon')); }
    });
    if (addBtn.hasAttribute('data-base')) {
      addBtn.setAttribute('data-price', Math.round((base + extra) * 100) / 100);
      addBtn.setAttribute('data-note', (picked ? picked.getAttribute('data-note') : '')
        + (withs.length ? (picked ? ', ' : '') + 'with ' + withs.join(' & ') : ''));
    }
    if (picked) {
      var price = picked.getAttribute('data-price'), note = picked.getAttribute('data-note');
      $('[data-szlabel]', card).textContent = note;
      $('[data-szprice]', card).textContent = money(parseFloat(price));
      $('.pbox-btn', card).setAttribute('aria-label', 'Size: ' + note + ', ' + money(parseFloat(price)) + '. Change size');
      var cz = $('[data-customize]', card);
      if (cz) cz.href = cz.href.replace(/&size=\d+$/, '') + '&size=' + picked.getAttribute('data-i');
    }
    var q = qtyOf(card);
    $('[data-total]', addBtn).textContent = money(parseFloat(addBtn.getAttribute('data-price')) * q);
    var minus = $('[data-step="-1"]', card);
    if (minus) minus.disabled = q <= 1;
  }

  /* the size box: a button that opens the list of sizes and their prices */
  function closeSizes(except) {
    $$('.pbox-btn[aria-expanded="true"]').forEach(function (b) {
      if (b === except) return;
      b.setAttribute('aria-expanded', 'false');
      b.nextElementSibling.hidden = true;
    });
  }
  function openSizes(btn, keyboard) {
    closeSizes(btn);
    btn.setAttribute('aria-expanded', 'true');
    btn.nextElementSibling.hidden = false;
    var on = $('[aria-selected="true"]', btn.nextElementSibling);
    // keyboard users land in the list; a tap or click just shows it
    if (on && keyboard) on.focus();
  }

  if (PAGE === 'category') {
    $$('[data-card]').forEach(paintCard);
    document.addEventListener('change', function (ev) {
      if (ev.target.matches('[data-addon]')) paintCard(ev.target.closest('[data-card]'));
    });
    document.addEventListener('keydown', function (ev) {
      var list = ev.target.closest('.pbox-menu');
      if (ev.key === 'Escape') {
        var open = $('.pbox-btn[aria-expanded="true"]');
        closeSizes();
        if (open) open.focus();
      } else if (list && (ev.key === 'ArrowDown' || ev.key === 'ArrowUp')) {
        ev.preventDefault();
        var opts = $$('[role="option"]', list), i = opts.indexOf(ev.target);
        opts[(i + (ev.key === 'ArrowDown' ? 1 : -1) + opts.length) % opts.length].focus();
      }
    });
    document.addEventListener('click', function (ev) {
      var box = ev.target.closest('.pbox-btn');
      if (box) {
        if (box.getAttribute('aria-expanded') === 'true') closeSizes(); else openSizes(box, ev.detail === 0);
        return;
      }
      var opt = ev.target.closest('.pbox-menu [role="option"]');
      if (opt) {
        var c = opt.closest('[data-card]');
        $$('[role="option"]', c).forEach(function (o) { o.setAttribute('aria-selected', String(o === opt)); });
        paintCard(c);
        closeSizes();
        if (ev.detail === 0) $('.pbox-btn', c).focus();
        return;
      }
      closeSizes();
      var step = ev.target.closest('[data-stepper] [data-step]');
      var card = ev.target.closest('[data-card]');
      if (step && card) {
        var out = $('[data-qty]', card);
        out.textContent = Math.max(1, Math.min(20, qtyOf(card) + parseInt(step.getAttribute('data-step'), 10)));
        paintCard(card);
        return;
      }
      var addBtn = ev.target.closest('[data-add]');
      if (addBtn && card) {
        var q = qtyOf(card), price = parseFloat(addBtn.getAttribute('data-price'));
        var note = addBtn.getAttribute('data-note') || '';
        var name = card.getAttribute('data-name');
        add(name, price, note === 'deal' ? '' : note, q);
        toast(addedText(q, name, note));
        addBtn.setAttribute('data-done', '');
        var label = addBtn.innerHTML;
        addBtn.textContent = 'Added';
        setTimeout(function () {
          addBtn.removeAttribute('data-done');
          addBtn.innerHTML = label;
          $('[data-qty]', card).textContent = '1';
          $$('[data-addon]', card).forEach(function (b) { b.checked = false; });
          paintCard(card);
        }, 1100);
      }
    });

    // the pill for this page sits in view, not scrolled off the end of the rail
    var track = $('[data-rail]'), on = track && $('[aria-current]', track);
    if (on) track.scrollLeft = on.offsetLeft - (track.clientWidth - on.offsetWidth) / 2;
  }

  /* ------------------------------------------------------------ the builder */
  if (PAGE === 'build' && window.PizzaConfig && window.BUILD) (function () {
    var B = window.BUILD, Q = new URLSearchParams(location.search);
    var root = $('.band-build'), stepsEl = $('[data-steps]');
    var deal = Q.get('deal') && (window.DEALS || {})[Q.get('deal')];
    var spec = Q.get('item') && (window.PIZZAS || {})[Q.get('item')];
    var size = parseInt(Q.get('size'), 10);
    if (!(size >= 0 && size < B.sizes.length)) size = 1;

    var cfgs = [], fixed = [], cur = 0, seen = [true], notes = [];
    if (deal) {
      deal.slots.forEach(function (s) {
        if (s.type === 'pizza') cfgs.push(new window.PizzaConfig({ size: s.size, included: s.included, dealPrice: deal.price }));
        else fixed.push(s.label);
      });
      $('[data-build-title]').textContent = deal.name;
      $('[data-build-sub]').textContent = deal.desc;
      document.title = deal.name + ' — Tasty Pizza, Dartmouth';
    } else if (spec) {
      cfgs.push(new window.PizzaConfig({ base: spec.prices, title: spec.name, tops: spec.tops, free: spec.free }));
      $('[data-build-title]').textContent = spec.name;
      $('[data-build-sub]').textContent = (spec.desc ? spec.desc + ' ' : '')
        + 'Change the size or crust, or add extra toppings.';
      document.title = spec.name + ' — Tasty Pizza, Dartmouth';
    } else {
      cfgs.push(new window.PizzaConfig({}));
    }
    if (!deal) cfgs[0].size = size;
    cfgs.forEach(function () { notes.push(''); });
    var qty = 1;

    function chips(cfg) {
      var sizes = B.sizes.map(function (s, i) {
        var on = i === cfg.size, dis = cfg.sizeLocked && !on;
        return '<button class="chip" type="button" data-size="' + i + '"' + (on ? ' data-on' : '')
          + (dis ? ' disabled' : '') + '>' + esc(s)
          + (cfg.base ? '<em>' + money(cfg.base[i]) + '</em>' : '') + '</button>';
      }).join('');
      var crusts = (window.CRUSTS || []).map(function (c) {
        return '<button class="chip" type="button" data-crust="' + esc(c.name) + '" data-sur="' + c.surcharge + '"'
          + (c.name === cfg.crust ? ' data-on' : '') + '>' + esc(c.name)
          + (c.surcharge ? '<em>+' + money(c.surcharge) + '</em>' : '') + '</button>';
      }).join('');
      return { sizes: sizes, crusts: crusts };
    }

    function step(n, title, extra, body) {
      return '<section class="step"><div class="step-h"><span class="step-n">' + n + '</span><h2>'
        + title + '</h2>' + (extra || '') + '</div>' + body + '</section>';
    }

    function renderSteps() {
      var cfg = cfgs[cur], c = chips(cfg), html = '';
      if (cfgs.length > 1) {
        html += '<div class="seg" role="tablist" aria-label="Pizzas in this deal">' + cfgs.map(function (x, i) {
          return '<button type="button" role="tab" data-pz="' + i + '" aria-selected="' + (i === cur) + '"'
            + (seen[i] && i !== cur ? ' data-set' : '') + '>Pizza ' + (i + 1) + '</button>';
        }).join('') + '</div>';
      }
      html += step(1, 'Size', cfg.sizeLocked ? '<em>set by the deal</em>' : '',
        '<div class="chips" data-sizes>' + c.sizes + '</div>');
      html += step(2, 'Crust', '', '<div class="chips" data-crusts>' + c.crusts + '</div>');
      html += step(3, 'Toppings', '<em data-cfg-count></em>',
        '<p class="ctrl-hint" data-cfg-hint></p><div class="tops-grid">' + cfg.toppingGrid() + '</div>'
        + '<p class="half-note">Half toppings: tap a topping, then pick the left or right half under it.</p>'
        + fixed.map(function (f) { return '<p class="fixedslot">' + esc(f) + '</p>'; }).join(''));
      html += step(4, 'Special toppings &amp; extra cheese', '',
        '<p class="ctrl-hint">Priced on their own, by size.</p><div class="tops-grid">'
        + cfg.toppingGrid((B.specials || []).map(function (x) { return x.name; })) + '</div>');
      html += step(5, 'Anything else?', '',
        '<textarea class="special" data-special rows="2" maxlength="140" '
        + 'placeholder="Well done, light sauce, cut in squares&hellip;">' + esc(notes[cur]) + '</textarea>');
      stepsEl.innerHTML = html;
    }

    function redrawPie() {
      var host = $('[data-tops]', root);
      host.innerHTML = '';
      cfgs[cur].tops.forEach(function (t) {
        for (var k = 0; k < t.qty; k++) cfgs[cur].sprinkle(root, t.name, t.side);
      });
    }

    function unitPrice() {
      return (deal ? deal.price : 0) + cfgs.reduce(function (s, c) { return s + c.price(); }, 0);
    }
    function describe(cfg, i) {
      var bits = [cfg.label()];
      if (cfg.crust !== 'White') bits.push(cfg.crust + ' crust');
      if (notes[i]) bits.push('“' + notes[i] + '”');
      return bits.join(', ');
    }

    var priceEl = $('[data-price]', root), addBtn = $('[data-build-add]', root);
    function summary(bump) {
      var cfg = cfgs[cur], rows = [];
      var which = $('[data-which]', root);
      which.hidden = false;
      which.textContent = deal ? deal.name : (spec ? B.sizes[cfg.size] + ' ' + spec.name : cfg.name());
      if (deal) {
        cfgs.forEach(function (c, i) { rows.push(['Pizza ' + (i + 1), describe(c, i)]); });
        fixed.forEach(function (f) { rows.push(['Included', f]); });
      } else {
        rows.push(['Size', B.sizes[cfg.size]]);
        rows.push(['Crust', cfg.crust + (cfg.sur ? ' +' + money(cfg.sur) : '')]);
        rows.push(['Toppings', cfg.label()]);
        if (notes[0]) rows.push(['Note', notes[0]]);
      }
      $('[data-lines]', root).innerHTML = rows.map(function (r) {
        return '<div><dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd></div>';
      }).join('');
      var total = unitPrice() * qty;
      priceEl.textContent = money(total);
      if (bump && !calm) { priceEl.removeAttribute('data-bump'); void priceEl.offsetWidth; priceEl.setAttribute('data-bump', ''); }
      var next = cfgs.length > 1 && cur < cfgs.length - 1 && !seen[cur + 1];
      addBtn.innerHTML = next ? 'Next: Pizza ' + (cur + 2)
        : 'Add to order · <b>' + money(total) + '</b>';
      var out = $('[data-buildqty] [data-qty]', root);
      out.textContent = qty;
      $('[data-buildqty] [data-step="-1"]', root).disabled = qty <= 1;
    }

    function show(i) {
      cur = i; seen[i] = true;
      renderSteps();
      redrawPie();
      cfgs[cur].paint(root, false);
      summary(false);
    }

    root.addEventListener('click', function (ev) {
      var t = ev.target, cfg = cfgs[cur];
      var pz = t.closest('[data-pz]');
      if (pz) { show(parseInt(pz.getAttribute('data-pz'), 10)); return; }
      var sz = t.closest('[data-size]');
      if (sz && !sz.disabled) {
        cfg.size = parseInt(sz.getAttribute('data-size'), 10);
        cfg.paint(root, true); summary(true); return;
      }
      var cr = t.closest('[data-crust]');
      if (cr) {
        cfg.crust = cr.getAttribute('data-crust');
        cfg.sur = parseFloat(cr.getAttribute('data-sur')) || 0;
        $$('[data-crusts] .chip', root).forEach(function (o) {
          if (o === cr) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
        });
        summary(true); return;
      }
      var sd = t.closest('[data-side]');
      if (sd) {
        // move this topping's pieces to the half picked
        var top = sd.closest('.topbtn').getAttribute('data-top'), side = sd.getAttribute('data-side');
        cfg.setSide(top, side);
        cfg.unsprinkle(root, top, true);
        for (var u = 0; u < cfg.qtyOf(top); u++) cfg.sprinkle(root, top, side);
        cfg.paint(root, true); summary(true); return;
      }
      if (t.closest('[data-sides]')) return;
      var ts = t.closest('[data-t]');
      var row = t.closest('.topbtn');
      if (row) {
        var name = row.getAttribute('data-top');
        var d = ts ? parseInt(ts.getAttribute('data-t'), 10) : 1;
        cfg.bump(name, d);
        if (d > 0) cfg.sprinkle(root, name, cfg.sideOf(name)); else cfg.unsprinkle(root, name, false);
        cfg.paint(root, true); summary(true); return;
      }
      var st = t.closest('[data-buildqty] [data-step]');
      if (st) { qty = Math.max(1, Math.min(20, qty + parseInt(st.getAttribute('data-step'), 10))); summary(true); return; }

      if (t.closest('[data-build-add]')) {
        if (cfgs.length > 1 && cur < cfgs.length - 1 && !seen[cur + 1]) {
          show(cur + 1);
          var top = $('.build-head', root).getBoundingClientRect().top + scrollY - 70;
          if (window.__lenis) window.__lenis.scrollTo(top); else scrollTo({ top: top, behavior: calm ? 'auto' : 'smooth' });
          return;
        }
        var name2, note;
        if (deal) {
          name2 = deal.name;
          note = cfgs.map(function (c, i) { return (cfgs.length > 1 ? 'Pizza ' + (i + 1) + ': ' : '') + describe(c, i); })
            .concat(fixed).join(' · ');
        } else {
          name2 = cfgs[0].name();
          note = describe(cfgs[0], 0);
        }
        add(name2, Math.round(unitPrice() * 100) / 100, note, qty);
        try { sessionStorage.setItem('tp.toast', addedText(qty, name2, '')); } catch (e) {}
        // back to the page the pizza was chosen from, at the spot it was left
        var ref = '';
        try { ref = new URL(document.referrer).pathname; } catch (e) {}
        if (cameFromHere() && !/build\.html$/.test(ref) && history.length > 1) history.back();
        else location.href = R + 'menu/pizza.html';
      }
    });
    root.addEventListener('input', function (ev) {
      if (ev.target.matches('[data-special]')) { notes[cur] = ev.target.value.trim(); summary(false); }
    });

    show(0);
  })();

  /* ------------------------------------------------------------ the order page */
  var linesEl = $('.band-order [data-lines]');
  function paintOrder() {
    if (!linesEl) return;
    var n = count();
    $('[data-empty]').hidden = n > 0;
    $('[data-full]').hidden = n === 0;
    linesEl.innerHTML = cart.map(function (r, i) {
      return '<li class="line" data-i="' + i + '"><div class="line-n"><b>' + esc(r.name) + '</b>'
        + (r.note ? '<small>' + esc(r.note) + '</small>' : '') + '<small>' + money(r.price) + ' each</small></div>'
        + '<div class="stepper"><button type="button" data-q="-1" aria-label="One fewer ' + esc(r.name) + '">&minus;</button>'
        + '<output>' + r.qty + '</output><button type="button" data-q="1" aria-label="One more ' + esc(r.name) + '">+</button></div>'
        + '<span class="line-p">' + money(r.price * r.qty) + '</span>'
        + '<button class="line-x" type="button" data-remove>Remove</button></li>';
    }).join('');
    var sub = cart.reduce(function (s, r) { return s + r.price * r.qty; }, 0);
    var rate = SHOP.taxRate || 0.14, tax = sub * rate;
    $('[data-sub]').textContent = money(sub);
    $('[data-taxlabel]').textContent = 'HST ' + Math.round(rate * 100) + '%';
    $('[data-tax]').textContent = money(tax);
    $('[data-total]').textContent = money(sub + tax);
    paintCount(false);
  }
  if (PAGE === 'order') {
    linesEl.addEventListener('click', function (ev) {
      var li = ev.target.closest('[data-i]');
      if (!li) return;
      var i = parseInt(li.getAttribute('data-i'), 10);
      var q = ev.target.closest('[data-q]');
      if (q) cart[i].qty += parseInt(q.getAttribute('data-q'), 10);
      if (ev.target.closest('[data-remove]')) cart[i].qty = 0;
      if (cart[i].qty <= 0) cart.splice(i, 1);
      save(); paintOrder();
    });
    var noteEl = $('[data-order-note]');
    try { noteEl.value = localStorage.getItem(NKEY) || ''; } catch (e) {}
    noteEl.addEventListener('input', function () {
      try { localStorage.setItem(NKEY, noteEl.value); } catch (e) {}
    });
    $('[data-checkout]').addEventListener('click', function () {
      var pay = $('[data-pay]'), note = noteEl.value.trim();
      $('[data-paynote]').hidden = !note;
      $('[data-paynote-text]').textContent = note;
      pay.hidden = false;
      this.hidden = true;
    });
    paintOrder();
  }

  /* ------------------------------------------------------------ the hero wheel

     Pizzas slide across right to left. The pies are cut out with an alpha
     edge, so what moves is the pizza itself and not a disc of white. Every
     slide links to the page that sells it. */
  (function () {
    var S = window.SLIDES || [];
    var stage = $('[data-wheelstage]');
    if (!stage || S.length < 2) return;

    var discs = $$('.disc', stage), ticks = $('[data-ticks]'), dealEl = $('[data-deal]');
    var badge = $('[data-badge]');
    var HOLD = 2000;
    if (ticks) ticks.style.setProperty('--hold', HOLD + 'ms');
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
      $('[data-dealname]', dealEl).textContent = s.name;
      dealEl.setAttribute('href', s.href);
      $('[data-dealcta]', dealEl).textContent = s.cta;
      $('[data-dealdesc]', dealEl).textContent = s.desc || '';
      var was = $('[data-dealwas]', dealEl), save = $('[data-dealsave]', dealEl);
      was.hidden = !s.was;
      save.hidden = false;
      if (s.was) {
        was.textContent = money(s.was);
        save.textContent = 'Save ' + money(s.was - s.price);
        save.className = 'save';
      } else {
        save.textContent = (s.unit ? s.unit + ' · ' : '') + (s.build ? 'from ' : '') + money(s.price);
        save.className = 'unit';
      }
      if (badge) {
        badge.querySelector('[data-badge-kick]').textContent = s.was ? 'Deal' : (s.build ? 'Build' : 'From');
        badge.querySelector('[data-badge-price]').textContent = money(s.price);
        badge.querySelector('[data-badge-was]').textContent = s.was ? money(s.was) : '';
        badge.setAttribute('data-pop', '');
      }
      dealEl.setAttribute('data-flash', '');
      requestAnimationFrame(function () {
        dealEl.removeAttribute('data-flash');
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
      wake(to);
      // park the incoming pie off the board with no transition, then release
      // it in the same frame the outgoing one leaves
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

    /* Reserve the tallest the offer block can ever be at this width, so the
       headline and buttons never jump as the slides turn. */
    var inner = $('.dealin', dealEl);
    function sizeDeal() {
      var f = ['[data-dealname]', '[data-dealdesc]', '[data-kicker]'].map(function (s) { return $(s, dealEl); });
      var keep = f.map(function (el) { return el.textContent; });
      inner.style.minHeight = '0px';
      var tall = 0;
      S.forEach(function (s) {
        f[0].textContent = s.name; f[1].textContent = s.desc || ''; f[2].textContent = s.kick;
        tall = Math.max(tall, inner.scrollHeight);
      });
      f.forEach(function (el, i) { el.textContent = keep[i]; });
      inner.style.minHeight = Math.ceil(tall) + 'px';
    }
    var rt;
    addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(sizeDeal, 140); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(sizeDeal);

    function start() { stop(); if (!calm) { timer = setInterval(function () { go(cur + 1, 1); }, HOLD); paint(); } }
    function stop() { clearInterval(timer); timer = null; }

    /* drag: the pizza follows your finger off the board; a tap follows the offer */
    var x0 = null, dx = 0, w = 1;
    stage.addEventListener('pointerdown', function (ev) {
      if (busy) return;
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
      else if (Math.abs(moved) < 6) { location.href = S[cur].href; return; }
      start();
    }
    stage.addEventListener('pointerup', release);
    stage.addEventListener('pointercancel', release);
    stage.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowRight') { stop(); go(cur + 1, 1); start(); }
      if (ev.key === 'ArrowLeft') { stop(); go(cur - 1, -1); start(); }
      if (ev.key === 'Enter') location.href = S[cur].href;
    });
    document.addEventListener('visibilitychange', function () { if (document.hidden) stop(); else start(); });
    addEventListener('pagehide', stop);
    addEventListener('pageshow', function (ev) { if (ev.persisted) start(); });

    /* the pizzas after the first arrive as data-src, so the first screen pays
       for one image, not five; they load once the page has, or on their turn */
    function wake(disc) {
      var img = disc && disc.querySelector('img[data-src]');
      if (img) { img.src = img.getAttribute('data-src'); img.removeAttribute('data-src'); }
    }
    if (document.readyState === 'complete') discs.forEach(wake);
    else addEventListener('load', function () { discs.forEach(wake); });

    sizeDeal(); start(); paint();
  })();

  /* ------------------------------------------------------------ go */
  paintClock();
  setInterval(paintClock, 60000);
  paintCount(false);
})();
