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
    // [{name, qty, side}] — side is 'whole', 'left' or 'right'
    this.tops = this.baseTops.map(function (n) { return { name: n, qty: 1, side: 'whole' }; });
  }

  /* Special toppings and extra cheese have their own price per size. They
     never count towards the toppings a price or a deal includes. */
  function special(name) {
    var list = root.BUILD.specials || [];
    for (var i = 0; i < list.length; i++) if (list[i].name === name) return list[i];
    return null;
  }
  Config.prototype.specialCost = function () {
    var self = this;
    return this.tops.reduce(function (s, t) {
      var sp = special(t.name);
      return s + (sp ? sp.prices[self.size] * t.qty : 0);
    }, 0);
  };

  Config.prototype.sideOf = function (name) {
    for (var i = 0; i < this.tops.length; i++) if (this.tops[i].name === name) return this.tops[i].side;
    return 'whole';
  };
  Config.prototype.setSide = function (name, side) {
    this.tops.forEach(function (t) { if (t.name === name) t.side = side; });
  };
  // "Pepperoni (left half)" — how the kitchen reads a topping
  function unit(t, n) {
    return (n > 1 ? n + '× ' : '') + t.name + (t.side && t.side !== 'whole' ? ' (' + t.side + ' half)' : '');
  }

  /* toppings put on beyond what the pizza comes with */
  Config.prototype.added = function () {
    var self = this;
    return this.tops.reduce(function (s, t) {
      if (special(t.name)) return s;
      return s + Math.max(0, t.qty - (self.baseTops.indexOf(t.name) >= 0 ? 1 : 0));
    }, 0);
  };

  Config.prototype.count = function () {
    return this.tops.reduce(function (s, t) { return s + (special(t.name) ? 0 : t.qty); }, 0);
  };

  Config.prototype.qtyOf = function (name) {
    for (var i = 0; i < this.tops.length; i++) if (this.tops[i].name === name) return this.tops[i].qty;
    return 0;
  };

  Config.prototype.bump = function (name, d) {
    var i = -1;
    for (var k = 0; k < this.tops.length; k++) if (this.tops[k].name === name) i = k;
    if (i < 0) { if (d > 0) this.tops.push({ name: name, qty: 1, side: 'whole' }); return; }
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
    var extra = this.extras() * B.extra[this.size] + this.specialCost() + this.sur;
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
      var more = [], halves = [];
      this.tops.forEach(function (t) {
        var own = self.baseTops.indexOf(t.name) >= 0;
        var n = t.qty - (own ? 1 : 0);
        if (n > 0) more.push(unit(t, n));
        else if (own && t.side !== 'whole') halves.push(unit(t, 1));
      });
      var bits = [];
      if (more.length) bits.push((this.free ? 'with ' : 'extra ') + more.join(', '));
      if (halves.length) bits.push(halves.join(', '));
      if (off.length) bits.push('no ' + off.join(', no '));
      return bits.length ? bits.join('; ') : 'as it comes';
    }
    if (!this.tops.length) return 'just cheese';
    return this.tops.map(function (t) { return unit(t, t.qty); }).join(', ');
  };

  Config.prototype.name = function () {
    var B = root.BUILD;
    if (this.dealPrice != null) return null;
    if (this.base) return B.sizes[this.size] + ' ' + this.title;
    var n = this.count();
    return B.sizes[this.size] + (n >= B.max ? ' ' + B.special : ' pizza');
  };

  /* ------------------------------------------------------------ markup */

  Config.prototype.toppingGrid = function (names) {
    var self = this;
    return (names || root.TOPPINGS || []).map(function (name) {
      var q = self.qtyOf(name);
      return '<div class="topbtn' + (q ? ' is-on' : '') + '" data-top="' + esc(name) + '">'
        + '<i class="tdot"></i>'
        + '<span class="topname">' + esc(name) + '</span>'
        + '<span class="topcost" data-topcost></span>'
        + '<span class="topq">'
        + (q ? '<button type="button" data-t="-1" aria-label="One less ' + esc(name) + '">&minus;</button>'
             + '<b>' + q + '</b>' : '')
        + '<button type="button" data-t="1" aria-label="Add ' + esc(name) + '">+</button>'
        + '</span><span class="sides" data-sides></span></div>';
    }).join('');
  };

  // left half, whole, right half — small pizzas to tap under a chosen topping
  var SIDES = [['left', 'Left half', 'M12 2a10 10 0 0 0 0 20z'],
               ['whole', 'Whole pizza', 'M12 2a10 10 0 1 0 0.01 0z'],
               ['right', 'Right half', 'M12 2a10 10 0 0 1 0 20z']];
  function sidePicker(name, side) {
    return SIDES.map(function (s) {
      return '<button type="button" data-side="' + s[0] + '" aria-pressed="' + (s[0] === side) + '" '
        + 'aria-label="' + esc(name) + ': ' + s[1] + '" title="' + s[1] + '">'
        + '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" '
        + 'stroke="currentColor" stroke-width="1.8"/><path d="' + s[2] + '" fill="currentColor"/></svg></button>';
    }).join('');
  }

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
      var sp = special(name), each = sp ? sp.prices[self.size] : cost;
      var c = b.querySelector('[data-topcost]');
      if (c) { c.textContent = each ? '+' + money(each) : ''; c.hidden = !each; }
      var sides = b.querySelector('[data-sides]');
      if (sides) sides.innerHTML = qty ? sidePicker(name, self.sideOf(name)) : '';
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

  /* the pieces that land on the dough, one set per unit of quantity; a half
     topping folds its spots onto that half, so it is just as evenly spread */
  Config.prototype.sprinkle = function (el, name, side) {
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
      if (side === 'left') p.x = Math.min(p.x, 100 - p.x, 47);
      if (side === 'right') p.x = Math.max(p.x, 100 - p.x, 53);
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

  // drawings for the special toppings and extra cheese, same 32-unit grid as the rest
  root.TOPPING_LOOK = root.TOPPING_LOOK || {};
  var MORE = {
    'Extra Cheese': { c: '#F7D46A', size: 22, svg:
      '<rect x="4" y="10" width="20" height="3.4" rx="1.7" transform="rotate(-25 14 12)" fill="#FBE08A"/>' +
      '<rect x="8" y="17" width="18" height="3.4" rx="1.7" transform="rotate(20 17 19)" fill="#F7D46A"/>' },
    'Zesty Chicken': { c: '#C98B4A', size: 22, svg:
      '<path d="M7 11c2-5 12-6 17-2s3 12-3 14-15 1-14-5z" fill="#C98B4A"/>' +
      '<path d="M10 12c3-3 9-3 12 0" stroke="#E0B07A" stroke-width="2" fill="none"/>' +
      '<circle cx="13" cy="17" r="1.2" fill="#B5432A"/><circle cx="19" cy="15" r="1" fill="#B5432A"/>' },
    'Sliced Steak': { c: '#6B3A22', size: 26, svg:
      '<path d="M4 18c4-6 18-9 24-4-3 4-17 9-24 4z" fill="#6B3A22"/>' +
      '<path d="M8 17c5-3 12-5 16-3" stroke="#8E5534" stroke-width="1.6" fill="none"/>' },
    'Parmesan Cheese': { c: '#F2E9CC', size: 20, svg:
      '<path d="M9 10l6-3 4 5-6 3z" fill="#FBF6E6"/><path d="M17 18l6-2 1 5-6 1z" fill="#F4EBD0"/>' +
      '<path d="M8 20l4-2 2 4-5 1z" fill="#FFFDF5"/>' },
    'Cheddar Cheese': { c: '#F29A2E', size: 22, svg:
      '<rect x="5" y="9" width="18" height="4" rx="2" transform="rotate(-20 14 11)" fill="#F29A2E"/>' +
      '<rect x="9" y="17" width="16" height="4" rx="2" transform="rotate(15 17 19)" fill="#E8861C"/>' },
    'Feta Cheese': { c: '#F5F2E8', size: 20, svg:
      '<rect x="8" y="8" width="9" height="9" rx="1.5" fill="#FFFFFF" stroke="#E6E1D3"/>' +
      '<rect x="16" y="15" width="8" height="8" rx="1.5" fill="#FBFAF4" stroke="#E6E1D3"/>' }
  };
  Object.keys(MORE).forEach(function (k) { if (!root.TOPPING_LOOK[k]) root.TOPPING_LOOK[k] = MORE[k]; });

  root.PizzaConfig = Config;
})(window);
