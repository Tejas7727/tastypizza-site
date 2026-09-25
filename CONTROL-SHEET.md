# The control sheet

`TastyPizza-Control.xlsx` is how the shop changes the website. Open it, change
something, save, close Excel, double-click **Publish website**. The live site
updates in about a minute.

## What the shop can change

| Sheet | Controls |
|---|---|
| **Home page** | The big slogan (a separate, shorter one for phones), the sentence under it, the three facts by the buttons |
| **Deals** | Every offer: on/off, name, wording, price, crossed-out price |
| **Menu** | Every dish: name, description, and each size's price |
| **Pizza builder** | What a build-your-own costs by topping count, and each extra topping |
| **Hours** | Opening and closing times, days off |
| **Shop details** | Phone, email, delivery fee and minimum, tax rate, DoorDash / Uber Eats / Skip links, the Google description |

Turning a deal off with `Showing = no` takes it off the site without deleting
it, so a seasonal offer can come back next year unchanged.

## How it is wired

```
TastyPizza-Control.xlsx
        |  scripts/control_sheet.py import
        v
     data/*.json          <- the single source of truth
        |  build.py -> storefront.py
        v
     docs/index.html      <- what GitHub Pages serves
```

`Publish website.bat` runs that chain and then commits and pushes. Every step
can stop it, and **nothing reaches the live site unless every step passes**:

1. **Import** refuses on a price that is not a number, an empty dish name, a
   crossed-out price that is not above the real one, an hour outside 0–26, a
   tax rate that looks like `14` instead of `0.14`. It names the sheet and the
   cell. Nothing is written when it refuses.
2. **Audit** re-checks the built page — missing alt text, no canonical, a
   broken photo reference, a deal pointing at a photo that does not exist.
3. Only then does it push.

So the worst case for a typo is a black window saying which cell is wrong,
while customers carry on seeing the old site.

## Two rules for whoever edits it

**Don't touch the grey columns.** They are how a row finds its way back to the
right dish. If one is changed or a row is deleted, that row is reported as
unknown and skipped rather than guessed at.

**Don't sort the sheets.** Rows are matched by the grey id, not by position, so
sorting will not corrupt anything — but it makes the sheet hard to read against
the site.

## Regenerating the workbook

The workbook is built from the JSON, so it can always be thrown away and remade:

```bash
python scripts/control_sheet.py export
```

Do that after anyone edits `data/` by hand, or after adding a dish, so the
sheet and the site agree again.

## What the sheet deliberately does not cover

Photos, the topping list, category structure, deal slots (which pizzas a deal
contains), and the hidden flags. These change rarely and are easy to break from
a spreadsheet. They stay in `data/*.json`.

Import never rewrites those files from scratch — it sets individual values in
the file already on disk. Everything the sheet has no column for survives
untouched. That is the reason for the whole design: a sheet that rebuilt the
JSON would silently delete whatever it did not know about.
