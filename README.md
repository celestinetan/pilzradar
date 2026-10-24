# Pilzradar Schweiz

**Where edible mushrooms are being found across Switzerland, canton by canton.**

👉 **Open it: [celestinetan.github.io/pilzradar](https://celestinetan.github.io/pilzradar/)**

Pilzradar brings together what a mushroom forager usually has to look up in a dozen places:

- **Recent finds**: verified records of 20 edible species from the last 30 days, on a map and as a list
- **Fruiting outlook**: a 0–100 score for the coming days, from rain and temperature forecasts for nine regions
- **Best spots**: places ranked by recent finds and past-season finds of species in season now
- **Species guide**: photos, seasons and the dangerous look-alikes for each species
- **Identify**: a step-by-step key that narrows down edibles and their look-alikes (a learning aid, not a verdict)
- **Safety**: official mushroom check points (Pilzkontrolle), picking rules and the poison helpline

It's one web page that works on phones and computers. No app, no account and no tracking.

> ⚠️ **Never eat a mushroom because of this site.** Pilzradar is for information and learning only. Get every find checked at an official [Pilzkontrolle](https://www.vapko.ch/index.php/de/eine-pilzkontrollstelle-finden) before eating. Suspected poisoning: call **Tox Info Suisse on 145**, or **144** in an emergency.

## How it stays up to date

A GitHub Action ([`.github/workflows/update.yml`](.github/workflows/update.yml)) runs four times a day. It runs [`scripts/update_data.py`](scripts/update_data.py), which:

1. fetches the latest weather forecast for nine Swiss regions from MET Norway, and
2. fetches the last 30 days of verified finds of the edible species from GBIF,

then writes them into `index.html` and `data.json` and commits the change. The script uses only the Python standard library.

Finds reach GBIF about two to three weeks after they are posted, so the newest finds shown are usually a little behind.

## Run your own copy

1. Fork this repository.
2. In your fork, open **Settings → Pages**, choose **Deploy from a branch**, then **main** and **/ (root)**, and save.
3. Open **Actions**, enable workflows, and run **Update finds and forecast** once by hand.

Your copy is then live at `https://<your-username>.github.io/pilzradar/`. To test locally, open `index.html` in a browser, or run `python scripts/update_data.py` to refresh the data.

## Data and credits

- **Finds:** [GBIF.org](https://www.gbif.org) occurrence data, mainly verified iNaturalist observations. Each find links to its GBIF record. Individual datasets carry their own licences (CC0, CC BY or CC BY-NC); see each record.
- **Forecasts:** [MET Norway](https://api.met.no), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Photos:** Wikimedia Commons. Each photo shows its author and licence, and links to its source. The photos stay under their own licences (mostly CC BY and CC BY-SA), not the licence of this code.
- **Check points:** Official municipal and VAPKO listings, checked in October 2026. Hours change every season, so check before you go.

Pilzradar is unofficial. It is not affiliated with or endorsed by GBIF, MET Norway, VAPKO, Tox Info Suisse, Wikimedia, Anthropic, Google or any other organisation named in it.

## Disclaimer and terms of use

Pilzradar is shared free of charge, for general information and learning only, and is provided "as is" without warranty of any kind. Finds, positions, forecasts, scores, species information and check-point hours come from third parties or are estimates, and can be wrong, rounded, out of date or missing. A spot on the map is not permission to enter land or pick there. You are responsible for what you pick, prepare and eat. To the fullest extent the law allows, the author accepts no liability for any illness, injury, death, loss or damage arising from using or relying on this site. The full terms are in the site under **Safety → Disclaimer & Terms of Use**.

This site was built with [Claude](https://claude.ai) and may contain errors.

## Licence

The code is released under the [MIT Licence](LICENSE). Data and photos keep their own licences (see above).

Made by [Celestine Tan](https://www.linkedin.com/in/celestinetan/) in Zürich.
