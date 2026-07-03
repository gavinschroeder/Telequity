# Telequity — local setup (cold start, macOS)

From a Mac with nothing installed to a running app. Two parts boot independently:
the **Python pipeline** and the **web console**. Neither needs external
credentials for the boot/demo path.

---

## 0. One-time system prerequisites

```bash
# Xcode command-line tools (git, compilers)
xcode-select --install

# Homebrew (package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# Apple Silicon: add brew to PATH if prompted
eval "$(/opt/homebrew/bin/brew shellenv)"

# Python 3.11 + Node LTS
brew install python@3.11 node
```

Verify: `python3.11 --version` (≥3.10), `node --version` (≥18).

---

## 1. Project root

```bash
cd ~/PycharmProjects/Telequity
```

---

## 2. Python pipeline

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env          # add CENSUS_API_KEY later for a REAL run
```

> If `geopandas` fails to install via pip (uncommon on Mac), either
> `brew install gdal` then retry, or install geopandas through conda.
> It is **not** needed for the demo boot.

**Boot check (no credentials):**

```bash
python scripts/run_texas_pilot.py --demo
pytest
```

Expected: `Demo gold tables written`, five `data/processed/*_DEMO.csv` files,
and `13 passed`.

---

## 3. Web console

```bash
cd web
npm install
cd server && npm install && cd ..
```

Run in two terminal tabs (both from `web/`):

```bash
npm run server      # tab 1 — token backend  :3001
npm run dev         # tab 2 — React app       :5173
```

Open **http://localhost:5173**. Expected: the styled console with the
seven-dashboard rail and an **"Awaiting Power BI setup"** card; the backend tab
logs `Not yet configured`. That is the correct booted state.

`npm run build` produces a production bundle in `web/dist/`.

---

## What boots without credentials vs. what needs setup

| Works on first boot | Needs setup later |
|---|---|
| Demo pipeline + gold CSVs | Real pipeline (CENSUS_API_KEY, broadband file/token, PNNL/LBNL + reference files) |
| All 13 tests | Live Power BI embed (publish `.pbix` + Azure service principal in `web/server/.env`) |
| Web console UI + backend health/not-configured state | — |

- Real pipeline data/credentials: see root `README.md` + `data/reference/README.md`.
- Power BI Embedded / Azure setup: see `web/README.md`.
- Building the `.pbix` needs Power BI Desktop (Windows) or the Power BI Service.
