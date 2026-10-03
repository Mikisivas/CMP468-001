# AgroPeace: GIS Early Warning and Real-Time Response for Farmer-Herder Conflict

CMP 468 (Computer Security) project 2. AgroPeace maps farmland, grazing reserves and stock routes, takes
incident reports by web, SMS and USSD, tracks herds with signed GPS pings, scores conflict risk per LGA,
sends multilingual alerts, and tracks mediation cases. Informant phone numbers are encrypted.

Default logins after setup: `admin`, `analyst`, `responder`, all with password `ChangeMe@468`.

---

## Part A. Step-by-step setup on your own laptop

### Step 1. Install Python 3.10 or newer
From https://www.python.org/downloads/ . On Windows tick **"Add python.exe to PATH"**.
Check: `python --version` (use `python3` on Linux/macOS).

### Step 2. Open a terminal in the project folder
```
cd C:\CMP468\project2-agropeace
```

### Step 3. Create a virtual environment and install packages
Windows:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Linux/macOS:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4. Generate your keys (do this once)
```
python manage.py genkey
```
It prints three lines for Windows and three for Linux. **Copy the lines for your system, paste them into
the terminal and press Enter.** Save them in a text file too, because:
- `AGROPEACE_DATA_KEY` encrypts reporter phone numbers. Lose it and they cannot be decrypted.
- `AGROPEACE_DEVICE_SECRET` signs GPS pings from herd devices.
- `AGROPEACE_SECRET_KEY` protects login sessions.

Every new terminal needs these three variables set again (paste the same lines).

### Step 5. Create the database and geography
```
python manage.py init
```
Creates 24 LGAs, farmland, grazing reserves, water points, the stock route, NDVI data, contacts and users.

### Step 6. Create training history and train the model
```
python manage.py history
python manage.py train
```
`train` prints AUC, precision and recall for logistic regression, random forest and a naive baseline,
and saves the best model with its SHA-256 hash in `data/`.

### Step 7. See the current risk ranking
```
python manage.py risk
```

### Step 8. Start the web application
```
python app.py
```
Open http://127.0.0.1:5050 and log in as `admin`. Leave this terminal running.
The map needs internet for the OpenStreetMap background. Without internet, risk circles, farms, routes and
herds still display on a plain background.

### Step 9. Start the live feed (second terminal)
Open a second terminal, activate the venv (Step 3), paste the key lines (Step 4), then:
```
python simulate.py --steps 40 --interval 2
```
Herds start moving on the map, SMS and USSD reports arrive, alerts appear on the right.

---

## Part B. Live demonstration script for the defence (about 7 minutes)

| # | Say this | Do this | What the panel sees |
|---|----------|---------|---------------------|
| 1 | "This is the conflict belt, ranked by risk." | Show map and risk table | Coloured LGA circles, top drivers per LGA |
| 2 | "Why is Guma high?" | Click Guma | Drivers list, rule score, ML probability, trend line |
| 3 | "Herds are moving south on the stock route." | Run `python simulate.py` | Cattle icons and trails move every 2 s |
| 4 | "A herd enters a yam farm in Guma." | Wait for step ~13 | Geofence alert in English, Hausa, Pidgin to peace committee, Ardo, farmers' rep, DPO |
| 5 | "A farmer with a basic phone sends an SMS." | (simulator sends) or see Part D | New red report dot, Guma score jumps |
| 6 | "False reports cause reprisals, so we verify." | Incidents page → Confirm or False | Credibility of that sender changes |
| 7 | "Informants are protected." | Point to "protected (encrypted)", then click Reveal | Number shown only to admin. Audit page logs it |
| 8 | "Warnings lead to action." | Mediation cases page | Case auto-opened for the attack, set mediator and status |
| 9 | "Attackers can't fake herd positions." | Run the curl command in Part D | HTTP 401 |
| 10 | "Anyone can report." | Log out, open /report | Public form with anonymous option |

---

## Part C. Moving towards a real deployment

1. **Real boundaries.** Download LGA boundaries (GRID3 Nigeria or OCHA HDX "nga_admbnda"). Load them into
   PostGIS or replace the coordinates in `geodata.py`.
2. **Real farms and routes.** Map farmland and stock routes with farmers' and herders' associations using
   QGIS or the free KoboToolbox / ODK Collect apps, export GeoJSON, insert into the `zones` table
   (`kind`, `name`, `lga`, `geojson`).
3. **Real conflict history.** Create a free account at https://acleddata.com, export Nigeria events as CSV, then:
   ```
   python manage.py import-acled path\to\acled_nigeria.csv
   python manage.py train
   ```
4. **Real NDVI.** In Google Earth Engine (free for research) run:
   ```javascript
   var lgas = ee.FeatureCollection('users/YOURNAME/nigeria_lgas');
   var ndvi = ee.ImageCollection('MODIS/061/MOD13Q1').select('NDVI');
   var months = ee.List.sequence(1, 12);
   var year = 2026;
   var out = ee.FeatureCollection(months.map(function (m) {
     var cur = ndvi.filter(ee.Filter.calendarRange(year, year, 'year'))
                   .filter(ee.Filter.calendarRange(m, m, 'month')).mean();
     var clim = ndvi.filter(ee.Filter.calendarRange(2005, year - 1, 'year'))
                    .filter(ee.Filter.calendarRange(m, m, 'month')).mean();
     return cur.addBands(clim.rename('clim')).multiply(0.0001)
       .reduceRegions({collection: lgas, reducer: ee.Reducer.mean(), scale: 250})
       .map(function (f) { return f.set({month: m, year: year}); });
   })).flatten();
   Export.table.toDrive({collection: out, description: 'ndvi_lga', fileFormat: 'CSV'});
   ```
   Load the CSV into the `ndvi` table (`lga, year, month, value, clim`).
5. **SMS and USSD.** Open an account with Africa's Talking or Termii. Point the inbound SMS callback to
   `https://YOUR-SERVER/api/sms` and the USSD callback to `https://YOUR-SERVER/api/ussd`. For outgoing alerts,
   set `alerts.sms_gateway.enabled` to `true` in `config.json` and set `AGROPEACE_SMS_KEY`.
6. **Herd devices.** A herder app or GPS collar sends:
   ```
   POST /api/herd_ping
   X-Timestamp: <unix time>
   X-Signature: hex(HMAC_SHA256(DEVICE_SECRET, timestamp + "." + body))
   {"herd_id": "HERD-07", "lat": 7.85, "lon": 8.83, "heads": 120}
   ```
   Tracking must be voluntary, agreed with herders' associations.
7. **Server.** Run behind Nginx with HTTPS (Let's Encrypt), as a systemd service, with keys in an
   environment file readable only by the service account. Back up the database daily (UniGuard from
   project 1 can do this).
8. **Policy.** Write a data protection policy under the NDPA 2023: who may reveal informants, retention of
   raw reports (for example 12 months), and annual review of user accounts.

---

## Part D. Manual tests you can show

SMS (works while `app.py` runs):
```
curl -X POST -d "from=08031234567&text=AP Guma CROP cows in yam farm at Yelwata" http://127.0.0.1:5050/api/sms
```
USSD, three steps of one session:
```
curl -X POST -d "phoneNumber=0803&text=" http://127.0.0.1:5050/api/ussd
curl -X POST -d "phoneNumber=0803&text=1*Guma" http://127.0.0.1:5050/api/ussd
curl -X POST -d "phoneNumber=0803&text=1*Guma*1" http://127.0.0.1:5050/api/ussd
```
Forged GPS ping (must fail with 401):
```
curl -i -X POST -H "Content-Type: application/json" -d "{\"herd_id\":\"FAKE\",\"lat\":7.8,\"lon\":8.8}" http://127.0.0.1:5050/api/herd_ping
```
On Windows PowerShell, use `curl.exe` instead of `curl`.

SMS keywords: `CROP` crop destruction, `RUSTLE` cattle theft, `COW` cattle killed, `THREAT`, `RUMOUR`,
`ROUTE` blocked route or water, `ATTACK`, `KILL`, `FLEE` displacement.

## Command reference

| Command | Purpose |
|---------|---------|
| `python manage.py genkey` | Generate encryption and signing keys |
| `python manage.py init` | Create database, geography, NDVI, contacts, users |
| `python manage.py history [--weeks 104]` | Synthetic incident history |
| `python manage.py import-acled FILE.csv` | Import real ACLED events |
| `python manage.py train` | Train and evaluate the risk model |
| `python manage.py risk [--top 10]` | Print risk ranking |
| `python app.py` | Run the web app and scheduler |
| `python simulate.py [--steps N --interval S]` | Live demo feed |

## Troubleshooting

- **"Set AGROPEACE_DATA_KEY"**: new terminal. Paste the key lines again (the same ones, not new ones).
- **Reporter numbers show `<undecryptable>`**: you generated new keys after `init`. Use the original keys or
  delete `data/agropeace.db` and run Steps 5 to 6 again.
- **Blank map background**: no internet for map tiles. Everything else still works.
- **Simulator gets HTTP 401**: the simulator terminal has a different `AGROPEACE_DEVICE_SECRET` from the server.
- **"Too many reports from this number"**: the per-number hourly limit (5) worked. Wait or use another number.
