"""Zaman Lafiya core: storage, geospatial functions, risk engine, alerting and security."""
import base64
import hashlib
import hmac
import json
import math
import os
import pickle
import sqlite3
import threading
import time
import urllib.request
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

import geodata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("ZAMANLAFIYA_CONFIG", os.path.join(BASE_DIR, "config.json"))
_lock = threading.RLock()

INCIDENT_TYPES = {
    # type: (label, severity 1-5)
    "crop_destruction": ("Crop destruction by cattle", 2),
    "cattle_rustling": ("Cattle rustling / theft", 3),
    "cattle_killing": ("Killing or maiming of cattle", 3),
    "threat": ("Threat or ultimatum", 2),
    "rumour": ("Rumour / hate speech", 1),
    "blocked_route": ("Blocked stock route or water point", 2),
    "armed_attack": ("Armed attack", 4),
    "killing": ("Killing of persons", 5),
    "displacement": ("Displacement of people", 4),
}
LEVELS = [(25, "Low", "green"), (50, "Moderate", "yellow"), (75, "High", "orange"), (101, "Severe", "red")]


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["database"] = _abs(cfg["database"])
    cfg["model_path"] = _abs(cfg["model_path"])
    return cfg


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)


# ---------------------------------------------------------------- database

SCHEMA = """
CREATE TABLE IF NOT EXISTS lgas (name TEXT PRIMARY KEY, state TEXT, lat REAL, lon REAL, baseline REAL);
CREATE TABLE IF NOT EXISTS zones (id INTEGER PRIMARY KEY, kind TEXT, name TEXT, lga TEXT, geojson TEXT);
CREATE TABLE IF NOT EXISTS ndvi (lga TEXT, year INTEGER, month INTEGER, value REAL, clim REAL,
  PRIMARY KEY (lga, year, month));
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, lga TEXT, lat REAL, lon REAL, type TEXT,
  severity INTEGER, fatalities INTEGER DEFAULT 0, description TEXT, source TEXT,
  reporter_hash TEXT, reporter_enc TEXT, verified INTEGER DEFAULT 0, credibility REAL DEFAULT 0.5);
CREATE INDEX IF NOT EXISTS idx_inc ON incidents(lga, ts);
CREATE TABLE IF NOT EXISTS herd_pings (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, herd_id TEXT,
  lat REAL, lon REAL, heads INTEGER);
CREATE INDEX IF NOT EXISTS idx_herd ON herd_pings(herd_id, ts);
CREATE TABLE IF NOT EXISTS risk_scores (ts REAL, lga TEXT, score REAL, level TEXT, rule_score REAL,
  ml_prob REAL, drivers TEXT);
CREATE INDEX IF NOT EXISTS idx_risk ON risk_scores(lga, ts);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, lga TEXT, level TEXT,
  kind TEXT, message TEXT, recipients TEXT, status TEXT DEFAULT 'sent', alert_key TEXT);
CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL, updated REAL,
  incident_id INTEGER, lga TEXT, status TEXT, mediator TEXT, notes TEXT, compensation_ngn REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, lga TEXT, role TEXT, name TEXT,
  phone_enc TEXT, language TEXT);
CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT, password TEXT);
CREATE TABLE IF NOT EXISTS reporters (reporter_hash TEXT PRIMARY KEY, reports INTEGER DEFAULT 0,
  confirmed INTEGER DEFAULT 0, rejected INTEGER DEFAULT 0, last_ts REAL);
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT,
  action TEXT, detail TEXT, prev_hash TEXT, entry_hash TEXT);
"""


def connect(cfg):
    conn = sqlite3.connect(cfg["database"], timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def q(cfg, sql, params=()):
    with _lock:
        conn = connect(cfg)
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()


def x(cfg, sql, params=()):
    with _lock:
        conn = connect(cfg)
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def xmany(cfg, sql, rows):
    with _lock:
        conn = connect(cfg)
        try:
            conn.executemany(sql, rows)
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------- security helpers

def fernet(cfg):
    key = os.environ.get(cfg["security"]["data_key_env"])
    if not key:
        raise SystemExit(f"Set {cfg['security']['data_key_env']} (run `python manage.py genkey`).")
    return Fernet(key.encode())


def encrypt_pii(cfg, value):
    return fernet(cfg).encrypt(value.encode()).decode() if value else None


def decrypt_pii(cfg, token):
    try:
        return fernet(cfg).decrypt(token.encode()).decode() if token else None
    except InvalidToken:
        return "<undecryptable>"


def pseudonym(cfg, phone):
    """Keyed hash: lets us rate-limit and score a reporter without storing the number in clear."""
    if not phone:
        return None
    pepper = os.environ.get(cfg["security"]["data_key_env"], "").encode()
    return hmac.new(pepper, phone.strip().encode(), hashlib.sha256).hexdigest()[:24]


def hash_password(pw, salt=None, it=310_000):
    salt = salt or os.urandom(16).hex()
    return f"pbkdf2_sha256${it}${salt}${hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(salt), it).hex()}"


def check_password(pw, stored):
    try:
        _, it, salt, dig = stored.split("$")
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex(), dig)


def device_signature(secret, body_bytes):
    return hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def audit(cfg, actor, action, detail=""):
    with _lock:
        last = q(cfg, "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        prev = last[0]["entry_hash"] if last else "GENESIS"
        ts = time.time()
        h = hashlib.sha256(f"{prev}|{ts}|{actor}|{action}|{detail}".encode()).hexdigest()
        x(cfg, "INSERT INTO audit_log(ts, actor, action, detail, prev_hash, entry_hash) VALUES (?,?,?,?,?,?)",
          (ts, actor, action, detail, prev, h))


def verify_audit(cfg):
    prev = "GENESIS"
    for r in q(cfg, "SELECT * FROM audit_log ORDER BY id"):
        h = hashlib.sha256(f"{prev}|{r['ts']}|{r['actor']}|{r['action']}|{r['detail']}".encode()).hexdigest()
        if r["prev_hash"] != prev or r["entry_hash"] != h:
            return False, r["id"]
        prev = h
    return True, None


# ---------------------------------------------------------------- geometry

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_in_polygon(lat, lon, ring):
    """Ray casting. ring is a list of [lon, lat]."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def distance_to_polygon_km(lat, lon, ring):
    if point_in_polygon(lat, lon, ring):
        return 0.0
    return min(_seg_dist_km(lat, lon, ring[i], ring[i + 1]) for i in range(len(ring) - 1))


def distance_to_line_km(lat, lon, coords):
    return min(_seg_dist_km(lat, lon, coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def _seg_dist_km(lat, lon, a, b):
    # local equirectangular projection is accurate enough at LGA scale
    kx = 111.32 * math.cos(math.radians(lat))
    ax, ay = (a[0] - lon) * kx, (a[1] - lat) * 110.57
    bx, by = (b[0] - lon) * kx, (b[1] - lat) * 110.57
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1e-12)))
    return math.hypot(ax + t * dx, ay + t * dy)


def nearest_lga(cfg, lat, lon, max_km=60):
    best, bd = None, 1e9
    for l in q(cfg, "SELECT name, lat, lon FROM lgas"):
        d = haversine_km(lat, lon, l["lat"], l["lon"])
        if d < bd:
            best, bd = l["name"], d
    return best if bd <= max_km else None


_zone_cache = {}


def zones(cfg, kind=None):
    if not _zone_cache:
        for z in q(cfg, "SELECT * FROM zones"):
            z["geom"] = json.loads(z["geojson"])
            _zone_cache.setdefault(z["kind"], []).append(z)
    if kind:
        return _zone_cache.get(kind, [])
    return [z for v in _zone_cache.values() for z in v]


# ---------------------------------------------------------------- seasonality & vegetation

def season_flags(dt):
    m = dt.month
    crop = 1.0 if 4 <= m <= 11 else 0.0               # crops in the field (planting to harvest)
    transhumance = 1.0 if m in (11, 12, 1, 2, 3, 4) else 0.0  # dry-season southward herd movement
    return crop, transhumance


def ndvi_anomaly(cfg, lga, year, month, table=None):
    """NDVI for this month minus the long-term mean for the same month (negative = drier than normal)."""
    if table is not None:
        return table.get((lga, year, month), 0.0)
    r = q(cfg, "SELECT value - clim AS a FROM ndvi WHERE lga=? AND year=? AND month=?", (lga, year, month))
    return r[0]["a"] if r else 0.0


# ---------------------------------------------------------------- features & risk

FEATURES = ["inc7", "inc30", "fatal30", "ndvi_anom", "crop", "transhumance", "rumours7", "baseline"]


def lga_features(cfg, lga, now=None, history=None, ndvi_table=None, baseline=None):
    """Feature vector for one LGA at time `now`. `history` lets training reuse preloaded rows."""
    now = now or time.time()
    rows = history if history is not None else q(
        cfg, "SELECT ts, type, severity, fatalities, verified FROM incidents WHERE lga=? AND ts BETWEEN ? AND ?",
        (lga, now - 30 * 86400, now))
    inc7 = inc30 = fatal30 = rumours7 = 0.0
    for r in rows:
        age = (now - r["ts"]) / 86400
        if age < 0 or age > 30:
            continue
        w = 1.0 if r["verified"] else 0.6
        if r["type"] == "rumour":
            if age <= 7:
                rumours7 += w
            continue
        inc30 += w
        fatal30 += r["fatalities"] or 0
        if age <= 7:
            inc7 += w * r["severity"] * math.exp(-age / 3.0)  # recent, severe events weigh most
    dt = datetime.fromtimestamp(now)
    crop, trans = season_flags(dt)
    if baseline is None:
        base = q(cfg, "SELECT baseline FROM lgas WHERE name=?", (lga,))
        baseline = base[0]["baseline"] if base else 0.3
    return {"inc7": round(inc7, 3), "inc30": inc30, "fatal30": fatal30,
            "ndvi_anom": round(ndvi_anomaly(cfg, lga, dt.year, dt.month, ndvi_table), 4), "crop": crop,
            "transhumance": trans, "rumours7": rumours7, "baseline": baseline}


def herd_pressure(cfg, lga, now=None, window_h=6, near_km=3.0):
    """Real-time layer: herds near or inside this LGA's farmland in the last few hours."""
    now = now or time.time()
    farms = [z for z in zones(cfg, "farmland") if z["lga"] == lga]
    if not farms:
        return {"herds_near": 0, "herds_inside": 0}
    pings = q(cfg, "SELECT herd_id, lat, lon, MAX(ts) AS ts FROM herd_pings WHERE ts > ? GROUP BY herd_id",
              (now - window_h * 3600,))
    near = inside = 0
    for p in pings:
        d = min(distance_to_polygon_km(p["lat"], p["lon"], f["geom"]["coordinates"][0]) for f in farms)
        if d == 0:
            inside += 1
        elif d <= near_km:
            near += 1
    return {"herds_near": near, "herds_inside": inside}


WEIGHTS = {"inc7": 0.35, "inc30": 0.10, "fatal30": 0.15, "drought": 6.0, "crop": 0.25,
           "transhumance": 0.35, "rumours7": 0.30, "baseline": 0.9, "herds_near": 0.35, "herds_inside": 0.9}


def rule_score(f, h):
    """Transparent weighted index (0-100). Returns score and the ranked drivers."""
    contrib = {
        "Recent incidents (7 days, severity weighted)": WEIGHTS["inc7"] * f["inc7"],
        "Incidents in last 30 days": WEIGHTS["inc30"] * f["inc30"],
        "Fatalities in last 30 days": WEIGHTS["fatal30"] * min(f["fatal30"], 10),
        "Vegetation deficit (NDVI below normal)": WEIGHTS["drought"] * max(0.0, -f["ndvi_anom"]),
        "Crops in the field": WEIGHTS["crop"] * f["crop"],
        "Dry-season herd movement": WEIGHTS["transhumance"] * f["transhumance"],
        "Rumours / hate speech reports": WEIGHTS["rumours7"] * f["rumours7"],
        "Historical violence baseline": WEIGHTS["baseline"] * f["baseline"],
        "Herds within 3 km of farms": WEIGHTS["herds_near"] * h["herds_near"],
        "Herds inside farmland": WEIGHTS["herds_inside"] * h["herds_inside"] * (1 + f["crop"]),
    }
    total = sum(contrib.values())
    score = 100 * (1 - math.exp(-total / 2.2))
    drivers = sorted(((k, round(v, 3)) for k, v in contrib.items() if v > 0), key=lambda kv: -kv[1])
    return round(score, 1), drivers


_model = {"obj": None, "mtime": None}


def load_model(cfg):
    """Load the trained model only if its SHA-256 matches the recorded value (no tampered pickles)."""
    path = cfg["model_path"]
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    if _model["mtime"] == mtime:
        return _model["obj"]
    with open(path, "rb") as fh:
        blob = fh.read()
    sha_file = path + ".sha256"
    if not os.path.exists(sha_file) or open(sha_file).read().strip() != hashlib.sha256(blob).hexdigest():
        audit(cfg, "system", "model_rejected", "hash mismatch")
        return None
    _model.update(obj=pickle.loads(blob), mtime=mtime)
    return _model["obj"]


def level_for(score):
    for limit, name, colour in LEVELS:
        if score < limit:
            return name, colour
    return "Severe", "red"


def compute_risk(cfg, now=None, store=True):
    now = now or time.time()
    model = load_model(cfg)
    out = []
    rows = []
    for l in q(cfg, "SELECT * FROM lgas"):
        f = lga_features(cfg, l["name"], now)
        h = herd_pressure(cfg, l["name"], now)
        rs, drivers = rule_score(f, h)
        prob = None
        if model:
            prob = float(model["model"].predict_proba([[f[k] for k in FEATURES]])[0][1])
            score = round(0.5 * rs + 0.5 * prob * 100, 1)
        else:
            score = rs
        # Hard trigger: a herd inside farmland during crop season is never "Low".
        if h["herds_inside"] and f["crop"]:
            score = max(score, 50.0)
        lvl, colour = level_for(score)
        item = {"lga": l["name"], "state": l["state"], "lat": l["lat"], "lon": l["lon"], "score": score,
                "level": lvl, "colour": colour, "rule_score": rs, "ml_prob": prob, "drivers": drivers[:4],
                "features": f, "herds": h}
        out.append(item)
        rows.append((now, l["name"], score, lvl, rs, prob, json.dumps(drivers[:4])))
    if store:
        xmany(cfg, "INSERT INTO risk_scores(ts, lga, score, level, rule_score, ml_prob, drivers) "
                   "VALUES (?,?,?,?,?,?,?)", rows)
    return sorted(out, key=lambda r: -r["score"])


# ---------------------------------------------------------------- alerts

TEMPLATES = {
    "en": "Zaman Lafiya {level} RISK alert for {lga} LGA ({state}). Main drivers: {drivers}. "
          "Peace committee, traditional rulers and security agencies should act now. Reply SAFE or HELP.",
    "ha": "Gargadi daga Zaman Lafiya: hadarin rikici ya kai matakin {level} a karamar hukumar {lga} ({state}). "
          "Shugabannin al'umma da jami'an tsaro su dauki mataki yanzu. Ka kwantar da hankali.",
    "pcm": "Zaman Lafiya alert: wahala fit happen for {lga} LGA ({state}), risk level na {level}. "
           "Make una no carry law for hand. Leaders and security, una suppose act now.",
}
ENCROACH = {
    "en": "Zaman Lafiya geofence alert: herd {herd} entered {zone}. Herder leader please move cattle back to "
          "the stock route. Farmers: do not confront, the peace committee has been notified.",
    "ha": "Gargadi: garken shanu {herd} ya shiga gona ({zone}). Shugaban makiyaya ya mayar da shanun hanyar burti.",
    "pcm": "Alert: cow group {herd} don enter {zone}. Herder leader abeg comot the cows go back to cattle route. "
           "Farmers, no fight, peace committee don hear.",
}


_sent = {}


def dispatch(cfg, lga, level, kind, message_by_lang, key):
    cooldown = cfg["alerts"]["cooldown_minutes"] * 60
    now = time.time()
    if key in _sent and now - _sent[key] < cooldown:
        return None
    _sent[key] = now
    recips = q(cfg, "SELECT * FROM contacts WHERE lga=? OR lga='*'", (lga,))
    sent_to = []
    for c in recips:
        msg = message_by_lang.get(c["language"], message_by_lang["en"])
        phone = decrypt_pii(cfg, c["phone_enc"])
        _send_sms(cfg, phone, msg)
        sent_to.append(f"{c['role']}:{c['name']}")
    aid = x(cfg, "INSERT INTO alerts(ts, lga, level, kind, message, recipients, alert_key) VALUES (?,?,?,?,?,?,?)",
            (now, lga, level, kind, message_by_lang["en"], ", ".join(sent_to), key))
    print(time.strftime("%H:%M:%S"), f"ALERT [{level}] {lga}: {message_by_lang['en'][:110]}", flush=True)
    return aid


def _send_sms(cfg, phone, text):
    gw = cfg["alerts"]["sms_gateway"]
    if not gw.get("enabled"):
        return  # demo mode: alerts are stored and shown on the dashboard only
    try:
        body = json.dumps({"to": phone, "sms": text[:459], "from": gw.get("sender_id", "ZamanLafiya"),
                           "api_key": os.environ.get(gw["api_key_env"], "")}).encode()
        req = urllib.request.Request(gw["url"], data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:
        print("SMS gateway error:", exc)


def evaluate_alerts(cfg, risks):
    threshold = cfg["alerts"]["min_level_score"]
    for r in risks:
        if r["score"] >= threshold:
            drivers = "; ".join(d[0] for d in r["drivers"][:3])
            msgs = {lang: t.format(level=r["level"].upper(), lga=r["lga"], state=r["state"], drivers=drivers)
                    for lang, t in TEMPLATES.items()}
            dispatch(cfg, r["lga"], r["level"], "risk", msgs, f"risk:{r['lga']}:{r['level']}")


def check_geofence(cfg, herd_id, lat, lon):
    """Called on every GPS ping. Returns list of events raised."""
    events = []
    crop, _ = season_flags(datetime.now())
    for f in zones(cfg, "farmland"):
        if point_in_polygon(lat, lon, f["geom"]["coordinates"][0]):
            lvl = "High" if crop else "Moderate"
            msgs = {k: v.format(herd=herd_id, zone=f["name"]) for k, v in ENCROACH.items()}
            if dispatch(cfg, f["lga"], lvl, "geofence", msgs, f"fence:{herd_id}:{f['id']}"):
                events.append({"type": "encroachment", "zone": f["name"], "lga": f["lga"]})
            break
    route = zones(cfg, "stock_route")
    if route:
        d = distance_to_line_km(lat, lon, route[0]["geom"]["coordinates"])
        lga = nearest_lga(cfg, lat, lon)
        if d > cfg["alerts"]["route_deviation_km"] and lga:
            msgs = {k: f"Zaman Lafiya: herd {herd_id} is {d:.1f} km off the official stock route near {lga}."
                    for k in TEMPLATES}
            if dispatch(cfg, lga, "Moderate", "route_deviation", msgs, f"dev:{herd_id}:{lga}"):
                events.append({"type": "route_deviation", "km": round(d, 1), "lga": lga})
    return events


# ---------------------------------------------------------------- incidents & reporters

def add_incident(cfg, lga, itype, description, source, lat=None, lon=None, phone=None, fatalities=0,
                 verified=0, ts=None):
    if itype not in INCIDENT_TYPES:
        raise ValueError("unknown incident type")
    if lga not in {l["name"] for l in q(cfg, "SELECT name FROM lgas")}:
        raise ValueError("unknown LGA")
    if lat is None or lon is None:
        l = q(cfg, "SELECT lat, lon FROM lgas WHERE name=?", (lga,))[0]
        lat, lon = l["lat"], l["lon"]
    rh = pseudonym(cfg, phone)
    cred = reporter_credibility(cfg, rh)
    if rh:
        last_hour = q(cfg, "SELECT COUNT(*) AS n FROM incidents WHERE reporter_hash=? AND ts > ?",
                      (rh, time.time() - 3600))[0]["n"]
        if last_hour >= cfg["security"]["max_reports_per_hour"] and cred < 0.7:
            raise PermissionError("rate limit: too many reports from this number")
        x(cfg, "INSERT INTO reporters(reporter_hash, reports, last_ts) VALUES (?,1,?) ON CONFLICT(reporter_hash) "
               "DO UPDATE SET reports=reports+1, last_ts=excluded.last_ts", (rh, time.time()))
    sev = INCIDENT_TYPES[itype][1]
    iid = x(cfg, "INSERT INTO incidents(ts, lga, lat, lon, type, severity, fatalities, description, source, "
                 "reporter_hash, reporter_enc, verified, credibility) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts or time.time(), lga, lat, lon, itype, sev, int(fatalities or 0), (description or "")[:500], source,
             rh, encrypt_pii(cfg, phone) if phone and cfg["security"]["store_reporter_phone"] else None,
             verified, cred))
    if sev >= 3 and ts is None:
        x(cfg, "INSERT INTO cases(created, updated, incident_id, lga, status, mediator, notes) VALUES (?,?,?,?,?,?,?)",
          (time.time(), time.time(), iid, lga, "reported", "", "Auto-opened for severity >= 3"))
    return iid


def reporter_credibility(cfg, rh):
    if not rh:
        return 0.4  # anonymous web report
    r = q(cfg, "SELECT confirmed, rejected FROM reporters WHERE reporter_hash=?", (rh,))
    if not r:
        return 0.5
    c, j = r[0]["confirmed"], r[0]["rejected"]
    return round((c + 1) / (c + j + 2), 2)  # Laplace-smoothed share of confirmed reports


def set_verification(cfg, incident_id, verified, actor):
    inc = q(cfg, "SELECT reporter_hash FROM incidents WHERE id=?", (incident_id,))
    if not inc:
        return
    x(cfg, "UPDATE incidents SET verified=? WHERE id=?", (1 if verified else -1, incident_id))
    if inc[0]["reporter_hash"]:
        col = "confirmed" if verified else "rejected"
        x(cfg, f"UPDATE reporters SET {col}={col}+1 WHERE reporter_hash=?", (inc[0]["reporter_hash"],))
    audit(cfg, actor, "verify_incident" if verified else "reject_incident", str(incident_id))


def parse_sms(text):
    """SMS format: ZL <LGA> <TYPE> <optional description>
    e.g. 'ZL Guma CROP cows destroyed yam farm at Yelwata'."""
    keywords = {"CROP": "crop_destruction", "RUSTLE": "cattle_rustling", "COW": "cattle_killing",
                "THREAT": "threat", "RUMOUR": "rumour", "ROUTE": "blocked_route", "ATTACK": "armed_attack",
                "KILL": "killing", "FLEE": "displacement"}
    parts = (text or "").strip().split()
    if len(parts) < 3 or parts[0].upper() != "ZL":
        return None
    # LGA names can have spaces: find the keyword position.
    for i in range(2, len(parts)):
        if parts[i].upper() in keywords:
            return {"lga": " ".join(parts[1:i]), "type": keywords[parts[i].upper()],
                    "description": " ".join(parts[i + 1:])}
    return None


def resolve_lga_name(cfg, name):
    names = [l["name"] for l in q(cfg, "SELECT name FROM lgas")]
    for n in names:
        if n.lower() == name.lower() or n.lower().split(" ")[0] == name.lower():
            return n
    return None
