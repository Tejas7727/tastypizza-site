# Tasty Pizza — website

760 Main St, Dartmouth NS · 902-435-5700

The whole site is built from four plain text files. **You never have to touch code to change
the menu, the prices, the offers or the hours.**

---

## Changing something on the website

Every change works the same way:

1. Open the file on GitHub (links below).
2. Click the **pencil** icon to edit.
3. Make your change.
4. Scroll down, click **Commit changes**.
5. Wait about a minute. The website updates itself.

| What you want to change | Open this file |
|---|---|
| A price, a new item, remove an item | [`data/menu.json`](data/menu.json) |
| Start or stop a deal | [`data/deals.json`](data/deals.json) |
| Hours, phone, email, delivery fee, address | [`data/site.json`](data/site.json) |
| Which 6 items show on the home page | [`data/site.json`](data/site.json) — the `hits` list |

Each of those files begins with plain-English instructions. Read the `_readme` at the top.

### The one rule

These files use commas and curly brackets. **Every `{ }` needs a comma after it except the
last one in a list.** If you get it wrong, the website does not break — the robot that builds
it refuses the change and emails you. Fix the comma and commit again.

### Changing a price — worked example

Find the line in `data/menu.json`:

```json
{ "name": "Donair", "desc": "Spiced beef off the spit...", "prices": [9.25, 11.35, 13.45, 15.55], ... }
```

The four numbers are Small, Medium, Large, Super — the same order as the `"sizes"` line just
above. Change `9.25` to `9.75`, commit, done.

### Stopping a deal

In `data/deals.json`, change `"active": true` to `"active": false`. The card disappears from
the site. Change it back whenever you want to run it again — nothing is lost.

---

## Real photos

Right now the food photos are **stock placeholders**. They are freely licensed and safe to
use, but they are not Tasty Pizza's food.

To replace one with a real photo:

1. Take the photo (a phone is fine — good daylight, plate near a window, shoot from above).
2. Name the file after the item, e.g. `donair.jpg`, `garlic-fingers.jpg`, `poutine.jpg`.
   The full list of names is in [`data/photos.json`](data/photos.json).
3. Put it in the `assets/photos-in/` folder.

That's it. The build picks up the real photo automatically and ignores the stock one. It also
crops, colour-corrects and compresses it for you.

---

## What the site does

- **Tap-to-call everywhere.** The old site's phone number was plain text — on a phone you
  could not tap it.
- **An order list.** Customers tap items to build a list, then call, copy it, email it, or
  jump to DoorDash or Uber Eats. It is not a checkout — it does not take payment.
- **A pizza builder** that prices itself from `menu.json` as you add toppings.
- **A live open/closed clock** in Halifax time, including the 2am Friday close.
- **Search and filters** on the menu — vegetarian, gluten free, donair, spicy and so on.
- **A map** that opens Google Maps directions in one tap.
- **Proper Google listing data** (hours, menu, price range, location) so the shop shows up
  correctly in search and on Maps.

---

## For a developer

No framework, no npm, no build tools. Python 3 standard library only, plus Pillow for images.

```bash
python build.py      # data/ + src/ -> docs/
python audit.py      # refuses to pass on dead links, missing images, bad SEO
```

```
data/      menu.json, site.json, deals.json, photos.json  <- all the content
src/       kit.py (chrome), site.css, app.js
scripts/   photo fetching, cropping/grading, fonts, favicon + share card
docs/      the built site — this is what GitHub Pages serves
assets/    fonts, brand files, and photos-in/ for real photography
```

`.github/workflows/build.yml` runs `build.py` then `audit.py` on every push and commits the
result. A failing audit blocks the deploy.

Photo licences: [`CREDITS.md`](CREDITS.md).

---

## Still to confirm with the owner

- **Honey Garlic Fingers** has no price (it had none on the old site either). It currently
  shows "Call for price".
- There is no drinks/pop section — the old site never had one.
- Real photography, as above.
