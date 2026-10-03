/* The pizza configurator.

   A pizza is not a product you pick off a list, it is something you build, and
   the price follows what you built. The old list showed "Cheese / 1 Topping /
   2 Toppings / 3 Toppings..." as if those were dishes — that was the shop's
   price table wearing a costume. Nobody orders "3 Toppings".

   This is the model behind build.html: build your own, customize a specialty
   pizza (it starts with its own toppings), or fill a deal's pizzas one after
   another with the size locked. tasty.js draws the page around it.

   Three rules the brief set:
   * never block a topping. Past the included count, show what the next one
     costs so the decision is informed rather than refused.
   * the same topping can be added twice. Double pepperoni is a real order.
   * size is chosen once. Inside a deal it is already decided, so it is shown
     but not changeable.
*/
(function (root) {
  'use strict';

  var money = function (n) { return '$' + (Math.round(n * 100) / 100).toFixed(2); };
  var esc = function (s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };

  function Config(opts) {
    var B = root.BUILD;
    this.sizeLocked = opts.size != null;
    this.size = opts.size != null ? opts.size : 1;
    this.included = opts.included != null ? opts.included : B.max;
    this.dealPrice = opts.dealPrice || null;   // set when this lives inside a deal
    this.base = opts.base || null;             // a specialty pizza's own prices, per size
    this.title = opts.title || null;
    // A specialty pizza starts with the toppings it comes with. Taking one off
    // costs nothing; anything added past them (and past `free`, the four
    // vegetables a Cheeseburger pizza includes) is an extra.
    this.baseTops = opts.tops || [];
    this.free = opts.free || 0;
    if (this.base) this.included = 0;
    this.crust = 'White';
    this.sur = 0;
    this.tops = this.baseTops.map(function (n) { return { name: n, qty: 1 }; });   // [{name, qty}]
  }

  /* toppings put on beyond what the pizza comes with */
  Config.prototype.added = function () {
    var self = this;
    return this.tops.reduce(function (s, t) {
      return s + Math.max(0, t.qty - (self.baseTops.indexOf(t.name) >= 0 ? 1 : 0));
    }, 0);
  };

  Config.prototype.count = function () {
    return this.tops.reduce(function (s, t) { return s + t.qty; }, 0);
  };

  Config.prototype.qtyOf = function (name) {
    for (var i = 0; i < this.tops.length; i++) if (this.tops[i].name === name) return this.tops[i].qty;
    return 0;
  };

  Config.prototype.bump = function (name, d) {
    var i = -1;
    for (var k = 0; k < this.tops.length; k++) if (this.tops[k].name === name) i = k;
    if (i < 0) { if (d > 0) this.tops.push({ name: name, qty: 1 }); return; }
    this.tops[i].qty += d;
    if (this.tops[i].qty <= 0) this.tops.splice(i, 1);
  };

  /* what one more topping costs right now — 0 while still inside the allowance */
  Config.prototype.nextCost = function () {
    var B = root.BUILD;
    if (this.base) return this.added() < this.free ? 0 : B.extra[this.size];
    if (this.count() < this.included) return 0;
    return B.extra[this.size];
  };

  Config.prototype.extras = function () {
    if (this.base) return Math.max(0, this.added() - this.free);
    return Math.max(0, this.count() - this.included);
  };

  Config.prototype.price = function () {
    var B = root.BUILD;
    var extra = this.extras() * B.extra[this.size] + this.sur;
    if (this.dealPrice != null) return extra;            // on top of the deal price
    if (this.base) return this.base[this.size] + extra;
    var n = Math.min(this.count(), B.prices.length - 1);
    return B.prices[n][this.size] + extra;
  };

  Config.prototype.label = function () {
    var self = this;
    if (this.base) {
      // say what changed from the pizza as it comes, which is what the kitchen needs
      var off = this.baseTops.filter(function (n) { return !self.qtyOf(n); });
      var more = [];
      this.tops.forEach(function (t) {
        var n = t.qty - (self.baseTops.indexOf(t.name) >= 0 ? 1 : 0);
        if (n > 0) more.push((n > 1 ? n + '× ' : '') + t.name);
      });
      var bits = [];
      if (more.length) bits.push((this.free ? 'with ' : 'extra ') + more.join(', '));
      if (off.length) bits.push('no ' + off.join(', no '));
      return bits.length ? bits.join('; ') : 'as it comes';
    }
    if (!this.count()) return 'just cheese';
    var parts = this.tops.map(function (t) {
      return t.qty > 1 ? t.qty + '× ' + t.name : t.name;
    });
    return parts.join(', ');
  };

  Config.prototype.name = function () {
    var B = root.BUILD;
    if (this.dealPrice != null) return null;
    if (this.base) return B.sizes[this.size] + ' ' + this.title;
    var n = this.count();
    return B.sizes[this.size] + (n >= B.max ? ' ' + B.special : ' pizza');
  };

  /* ------------------------------------------------------------ markup */

  Config.prototype.toppingGrid = function () {
    var self = this;
    return (root.TOPPINGS || []).map(function (name) {
      var q = self.qtyOf(name);
      return '<div class="topbtn' + (q ? ' is-on' : '') + '" data-top="' + esc(name) + '">'
        + '<i class="tdot"></i>'
        + '<span class="topname">' + esc(name) + '</span>'
        + '<span class="topcost" data-topcost></span>'
        + '<span class="topq">'
        + (q ? '<button type="button" data-t="-1" aria-label="One less ' + esc(name) + '">&minus;</button>'
             + '<b>' + q + '</b>' : '')
        + '<button type="button" data-t="1" aria-label="Add ' + esc(name) + '">+</button>'
        + '</span></div>';
    }).join('');
  };

  /* ------------------------------------------------------------ painting */

  Config.prototype.paint = function (el, bump) {
    var B = root.BUILD, self = this;
    var q = function (s) { return el.querySelector(s); };
    var all = function (s) { return Array.prototype.slice.call(el.querySelectorAll(s)); };

    var n = this.count();
    var cnt = q('[data-cfg-count]');
    if (cnt) {
      cnt.textContent = this.base
        ? (this.free ? Math.min(this.added(), this.free) + ' of ' + this.free + ' included' : '')
          + (this.extras() ? (this.free ? ' · ' : '') + this.extras() + ' extra' : '')
        : this.extras() ? n + ' · ' + this.extras() + ' extra'
        : n + ' of ' + this.included;
    }

    var hint = q('[data-cfg-hint]');
    if (hint) {
      var each = 'Each extra topping is ' + money(B.extra[this.size]) + ' on this size.';
      hint.textContent = this.base
        ? (this.added() < this.free ? 'Pick ' + (this.free - this.added()) + ' more at no charge — vegetables are the classic. '
          : 'The filled ones come on it; tap − to leave one off. ' + each)
        : n < this.included ? (this.included - n) + ' more included' : each;
      hint.hidden = false;
    }

    // once the allowance is used up, every topping wears its price
    var cost = this.nextCost();
    all('.topbtn').forEach(function (b) {
      var name = b.getAttribute('data-top');
      var qty = self.qtyOf(name);
      b.classList.toggle('is-on', qty > 0);
      var look = root.TOPPING_LOOK[name];
      var dot = b.querySelector('.tdot');
      if (look && dot && !dot.style.background) dot.style.background = look.c;
      var c = b.querySelector('[data-topcost]');
      if (c) { c.textContent = cost ? '+' + money(cost) : ''; c.hidden = !cost; }
      var box = b.querySelector('.topq');
      if (box) {
        box.innerHTML = (qty
          ? '<button type="button" data-t="-1" aria-label="One less ' + esc(name) + '">&minus;</button>'
            + '<b>' + qty + '</b>' : '')
          + '<button type="button" data-t="1" aria-label="Add ' + esc(name) + '">+</button>';
      }
    });

    var dough = q('[data-dough]');
    if (dough) {
      if (n) dough.setAttribute('data-topped', ''); else dough.removeAttribute('data-topped');
      dough.style.width = [78, 86, 94, 100][this.size] + '%';
    }


    all('[data-sizes] .chip').forEach(function (b) {
      var on = parseInt(b.getAttribute('data-size'), 10) === self.size;
      if (on) b.setAttribute('data-on', ''); else b.removeAttribute('data-on');
    });

    // a deal showing its running total needs to hear about every tap, not just
    // the one that closes the slot
    if (this.onChange) this.onChange(this);
  };

  /* Where the pieces land. Each topping's seven pieces point seven different
     ways (3/7 of a turn apart) and sit at seven different distances from the
     centre (equal-area rings), so one topping alone already covers middle to
     rim. Each next topping ("lane") is turned by the golden angle and shifted
     a ring, so it fills the gaps instead of landing on top. A ninth topping
     reuses a lane with half a ring of offset. */
  var LANES = 8, PER = 7;
  function spot(lane, k, layer) {
    var ring = (k + lane * 0.37 + layer * 0.5) % PER;
    var r = 40 * Math.sqrt((ring + 0.5) / PER);                    // % of the topping area
    var a = k * (Math.PI * 2 * 3 / PER) + lane * 2.39996 + layer * 0.9;
    return { x: 50 + Math.cos(a) * r, y: 50 + Math.sin(a) * r };
  }

  /* the pieces that land on the dough, one set per unit of quantity */
  Config.prototype.sprinkle = function (el, name) {
    var host = el.querySelector('[data-tops]'), look = root.TOPPING_LOOK[name];
    if (!host || !look) return;
    var used = [];
    for (var u = 0; u < LANES; u++) used.push(0);
    Array.prototype.forEach.call(host.querySelectorAll('.bit[data-lane]'), function (b) {
      used[+b.getAttribute('data-lane')] += 1 / PER;
    });
    var lane = 0;
    for (var l = 1; l < LANES; l++) if (used[l] < used[lane] - 0.01) lane = l;
    var layer = Math.round(used[lane]);
    for (var k = 0; k < PER; k++) {
      var j = k * LANES + lane, p = spot(lane, k, layer);
      var bit = document.createElement('span');
      bit.className = 'bit';
      bit.setAttribute('data-for', name);
      bit.setAttribute('data-lane', lane);
      bit.style.left = p.x.toFixed(2) + '%';
      bit.style.top = p.y.toFixed(2) + '%';
      // sized against the pizza, so the pieces stay in scale on any size of drawing
      bit.style.setProperty('--w', (look.size / 1.9 * (0.9 + ((j * 13) % 7) / 30)).toFixed(2) + '%');
      bit.style.setProperty('--rot', ((j * 137) % 360) + 'deg');
      bit.style.animationDelay = (k * 34) + 'ms';
      bit.innerHTML = '<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">' + look.svg + '</svg>';
      host.appendChild(bit);
    }
  };

  Config.prototype.unsprinkle = function (el, name, all) {
    var bits = Array.prototype.slice.call(
      el.querySelectorAll('[data-tops] [data-for="' + name.replace(/"/g, '') + '"]'));
    var drop = all ? bits.length : 7;
    bits.slice(-drop).forEach(function (b) { b.remove(); });
  };

  root.PizzaConfig = Config;
})(window);
