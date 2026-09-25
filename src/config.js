/* The pizza configurator.

   A pizza is not a product you pick off a list, it is something you build, and
   the price follows what you built. The old list showed "Cheese / 1 Topping /
   2 Toppings / 3 Toppings..." as if those were dishes — that was the shop's
   price table wearing a costume. Nobody orders "3 Toppings".

   So: one "Build Your Own Pizza" row that expands in place into the builder.
   Deals that contain pizzas expand into slots — Pizza 1, Pizza 2 — and each
   slot expands again into the same builder with its size locked.

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
    this.crust = 'White';
    this.sur = 0;
    this.tops = [];                            // [{name, qty}]
  }

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
    if (this.count() < this.included) return 0;
    return B.extra[this.size];
  };

  Config.prototype.extras = function () {
    return Math.max(0, this.count() - this.included);
  };

  Config.prototype.price = function () {
    var B = root.BUILD;
    var extra = this.extras() * B.extra[this.size] + this.sur;
    if (this.dealPrice != null) return extra;            // on top of the deal price
    var n = Math.min(this.count(), B.prices.length - 1);
    return B.prices[n][this.size] + extra;
  };

  Config.prototype.label = function () {
    if (!this.count()) return 'just cheese';
    var parts = this.tops.map(function (t) {
      return t.qty > 1 ? t.qty + '× ' + t.name : t.name;
    });
    return parts.join(', ');
  };

  Config.prototype.name = function () {
    var B = root.BUILD;
    if (this.dealPrice != null) return null;
    var n = this.count();
    return B.sizes[this.size] + (n >= B.max ? ' ' + B.special : ' pizza');
  };

  /* ------------------------------------------------------------ markup */

  Config.prototype.render = function () {
    var B = root.BUILD, self = this;

    var sizes = B.sizes.map(function (s, i) {
      var on = i === self.size;
      var dis = self.sizeLocked && !on;
      return '<button class="chip" type="button" data-size="' + i + '"'
        + (on ? ' data-on' : '') + (dis ? ' disabled aria-disabled="true"' : '')
        + '>' + esc(s) + '</button>';
    }).join('');

    var crusts = (root.CRUSTS || []).map(function (c, i) {
      return '<button class="chip" type="button" data-crust="' + esc(c.name) + '"'
        + ' data-sur="' + c.surcharge + '"' + (i === 0 ? ' data-on' : '') + '>'
        + esc(c.name) + (c.surcharge ? '<em>+' + money(c.surcharge) + '</em>' : '') + '</button>';
    }).join('');

    return ''
      + '<div class="cfg">'
      + '  <div class="cfg-stage">'
      + '    <div class="peel"><span class="peel-board"></span>'
      + '      <div class="dough" data-dough><span class="sauce"></span><span class="cheese"></span>'
      + '        <div class="tops" data-tops></div></div></div>'
      + '    <p class="readout"><b data-cfg-price>' + money(this.price()) + '</b>'
      + '      <span data-cfg-note>just cheese</span></p>'
      + '  </div>'
      + '  <div class="cfg-ctrl">'
      + '    <div class="ctrl"><h3>Size' + (this.sizeLocked
            ? ' <em>set by the deal</em>' : '') + '</h3>'
      + '      <div class="chips" data-sizes>' + sizes + '</div></div>'
      + '    <div class="ctrl"><h3>Crust</h3><div class="chips" data-crusts>' + crusts + '</div></div>'
      + '    <div class="ctrl"><h3>Toppings <em data-cfg-count></em></h3>'
      + '      <p class="ctrl-hint" data-cfg-hint></p>'
      + '      <div class="tops-grid" data-topgrid>' + this.toppingGrid() + '</div></div>'
      + '    <button class="btn btn-red btn-wide" type="button" data-cfg-add>'
      + '      <span data-cfg-cta>Add to my order</span></button>'
      + '  </div>'
      + '</div>';
  };

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

    var p = q('[data-cfg-price]');
    if (p) {
      p.textContent = (this.dealPrice != null && this.price() === 0) ? 'Included' : money(this.price());
      if (bump) { p.setAttribute('data-bump', ''); setTimeout(function () { p.removeAttribute('data-bump'); }, 320); }
    }
    var note = q('[data-cfg-note]');
    if (note) note.textContent = B.sizes[this.size] + ' · ' + this.label();

    var n = this.count();
    var cnt = q('[data-cfg-count]');
    if (cnt) {
      cnt.textContent = this.extras()
        ? n + ' · ' + this.extras() + ' extra'
        : n + ' of ' + this.included;
    }

    var hint = q('[data-cfg-hint]');
    if (hint) {
      hint.textContent = n < this.included
        ? (this.included - n) + ' more included'
        : 'Every extra topping is ' + money(B.extra[this.size]) + ' on this size.';
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

    var cta = q('[data-cfg-cta]');
    if (cta) {
      cta.textContent = this.dealPrice != null
        ? (this.price() > 0 ? 'Save this pizza · +' + money(this.price()) : 'Save this pizza')
        : 'Add to my order · ' + money(this.price());
    }

    all('[data-sizes] .chip').forEach(function (b) {
      var on = parseInt(b.getAttribute('data-size'), 10) === self.size;
      if (on) b.setAttribute('data-on', ''); else b.removeAttribute('data-on');
    });

    // a deal showing its running total needs to hear about every tap, not just
    // the one that closes the slot
    if (this.onChange) this.onChange(this);
  };

  /* the pieces that land on the dough, one per unit of quantity */
  Config.prototype.sprinkle = function (el, name) {
    var host = el.querySelector('[data-tops]'), look = root.TOPPING_LOOK[name];
    if (!host || !look) return;
    var seq = host.querySelectorAll('[data-for="' + name.replace(/"/g, '') + '"]').length;
    for (var i = 0; i < 7; i++) {
      var bit = document.createElement('span');
      bit.className = 'bit';
      bit.setAttribute('data-for', name);
      var ang = (i + seq * 3) * 2.399 + Math.random() * 0.7;
      var rad = 13 + Math.sqrt((i + 0.55) / 7) * 31;
      bit.style.left = (50 + Math.cos(ang) * rad) + '%';
      bit.style.top = (50 + Math.sin(ang) * rad) + '%';
      bit.style.setProperty('--w', (look.size * (0.86 + Math.random() * 0.28)).toFixed(1) + 'px');
      bit.style.setProperty('--rot', Math.round(Math.random() * 360) + 'deg');
      bit.style.animationDelay = (i * 34) + 'ms';
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

  /* ------------------------------------------------------------ wiring */

  Config.prototype.mount = function (el, onAdd) {
    var self = this;
    el.addEventListener('click', function (ev) {
      var t = ev.target;

      var size = t.closest('[data-size]');
      if (size && !size.disabled) {
        self.size = parseInt(size.getAttribute('data-size'), 10);
        self.paint(el, true);
        return;
      }
      var crust = t.closest('[data-crust]');
      if (crust) {
        self.crust = crust.getAttribute('data-crust');
        self.sur = parseFloat(crust.getAttribute('data-sur')) || 0;
        Array.prototype.slice.call(el.querySelectorAll('[data-crusts] .chip')).forEach(function (o) {
          if (o === crust) o.setAttribute('data-on', ''); else o.removeAttribute('data-on');
        });
        self.paint(el, true);
        return;
      }
      var step = t.closest('[data-t]');
      if (step) {
        var btn = step.closest('.topbtn');
        var name = btn.getAttribute('data-top');
        var d = parseInt(step.getAttribute('data-t'), 10);
        self.bump(name, d);
        if (d > 0) self.sprinkle(el, name); else self.unsprinkle(el, name, false);
        self.paint(el, true);
        return;
      }
      // tapping the body of an unselected topping adds one, same as +
      var row = t.closest('.topbtn');
      if (row) {
        var nm = row.getAttribute('data-top');
        self.bump(nm, 1);
        self.sprinkle(el, nm);
        self.paint(el, true);
        return;
      }
      if (t.closest('[data-cfg-add]')) { onAdd(self); return; }
    });
    this.paint(el, false);
  };

  root.PizzaConfig = Config;
})(window);
