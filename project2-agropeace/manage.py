"""AgroPeace management commands. Run `python manage.py --help`."""
import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import random
import secrets
import time
from datetime import datetime

from cryptography.fernet import Fernet

import core
import geodata


def cmd_genkey(a):
    k = Fernet.generate_key().decode()
    d = secrets.token_hex(24)
    s = secrets.token_hex(32)
    print("Keep these secret. Set them in your terminal before running AgroPeace.\n")
    print("Windows (PowerShell):")
    print(f'  $env:AGROPEACE_DATA_KEY="{k}"\n  $env:AGROPEACE_DEVICE_SECRET="{d}"\n  $env:AGROPEACE_SECRET_KEY="{s}"\n')
    print("Linux / macOS:")
    print(f"  export AGROPEACE_DATA_KEY='{k}'\n  export AGROPEACE_DEVICE_SECRET='{d}'\n  export AGROPEACE_SECRET_KEY='{s}'")


def cmd_init(a):
    cfg = core.load_config()
    os.makedirs(os.path.dirname(cfg["database"]), exist_ok=True)
    core.xmany(cfg, "INSERT OR REPLACE INTO lgas(name, state, lat, lon, baseline) VALUES (?,?,?,?,?)", geodata.LGAS)
    core.x(cfg, "DELETE FROM zones")
    core.xmany(cfg, "INSERT INTO zones(kind, name, lga, geojson) VALUES (?,?,?,?)",
               [(k, n, l, json.dumps(g)) for k, n, l, g in geodata.build_zones()])
    seed_ndvi(cfg)
    seed_contacts(cfg)
    pw = os.environ.get("AGROPEACE_ADMIN_PASSWORD", "ChangeMe@468")
    for user, role in (("admin", "admin"), ("analyst", "analyst"), ("responder", "responder")):
        core.x(cfg, "INSERT OR IGNORE INTO users(username, role, password) VALUES (?,?,?)",
               (user, role, core.hash_password(pw)))
    core.audit(cfg, "cli", "init", "database initialised")
    print(f"Initialised {cfg['database']}: {len(geodata.LGAS)} LGAs, zones, NDVI, contacts.")
    print(f"Users admin / analyst / responder, password: {pw}")


def seed_ndvi(cfg, years=3):
    """Synthetic monthly NDVI (stand-in for MODIS MOD13Q1). Northern LGAs are drier.
    Some LGA-years get a drought shock so the model has something to learn."""
    rnd = random.Random(11)
    now = datetime.now()
    rows = []
    for name, _, lat, _, _ in geodata.LGAS:
        for y in range(now.year - years + 1, now.year + 1):
            drought = rnd.random() < 0.3
            for m in range(1, 13):
                clim = 0.62 - 0.035 * (lat - 7) + 0.22 * math.sin((m - 5) / 12 * 2 * math.pi)
                shock = -rnd.uniform(0.06, 0.15) if drought and m in (3, 4, 5, 6, 10, 11, 12) else 0
                rows.append((name, y, m, round(clim + shock + rnd.gauss(0, 0.02), 4), round(clim, 4)))
    # make the current month visibly dry in a few hotspot LGAs for the demo
    for name in ("Guma", "Bokkos", "Agatu", "Keana"):
        lat = [l[2] for l in geodata.LGAS if l[0] == name][0]
        clim = 0.62 - 0.035 * (lat - 7) + 0.22 * math.sin((now.month - 5) / 12 * 2 * math.pi)
        rows.append((name, now.year, now.month, round(clim - 0.12, 4), round(clim, 4)))
    core.xmany(cfg, "INSERT OR REPLACE INTO ndvi(lga, year, month, value, clim) VALUES (?,?,?,?,?)", rows)


def seed_contacts(cfg):
    rnd = random.Random(5)
    core.x(cfg, "DELETE FROM contacts")
    rows = []
    for name, state, *_ in geodata.LGAS:
        for role, lang in (("LGA Peace Committee Chair", "en"), ("Ardo / Herders' Association", "ha"),
                           ("Farmers' Association (AFAN) Rep", "pcm"), ("Divisional Police Officer", "en")):
            phone = "080" + str(rnd.randint(30000000, 99999999))
            rows.append((name, role, f"{role.split(' ')[0]} {name}", core.encrypt_pii(cfg, phone), lang))
    rows.append(("*", "State Emergency Operations Centre", "SEOC Duty Officer",
                 core.encrypt_pii(cfg, "08000000000"), "en"))
    core.xmany(cfg, "INSERT INTO contacts(lga, role, name, phone_enc, language) VALUES (?,?,?,?,?)", rows)


def cmd_history(a):
    """Generate a synthetic incident history with seasonality, drought effects and
    self-excitation (violence begets reprisals), similar in spirit to Hawkes models."""
    cfg = core.load_config()
    rnd = random.Random(a.seed)
    core.x(cfg, "DELETE FROM incidents WHERE source='synthetic'")
    now = time.time()
    start = now - a.weeks * 7 * 86400
    ndvi = {(r["lga"], r["year"], r["month"]): r["value"] - r["clim"]
            for r in core.q(cfg, "SELECT * FROM ndvi")}
    types = list(core.INCIDENT_TYPES)
    weights = [18, 12, 8, 10, 14, 6, 9, 7, 4]
    rows = []
    for name, state, lat, lon, base in geodata.LGAS:
        recent = []
        t = start
        while t < now - 86400:
            dt = datetime.fromtimestamp(t)
            crop, trans = core.season_flags(dt)
            anom = ndvi.get((name, dt.year, dt.month), 0.0)
            excite = sum(math.exp(-(t - e) / (4 * 86400)) for e in recent if t - e < 30 * 86400)
            lam = 0.004 + 0.022 * base * (1 + 0.9 * trans + 0.5 * crop) * (1 + 9 * max(0, -anom)) + 0.13 * excite
            n = _poisson(rnd, lam)  # expected events per day
            for _ in range(n):
                ts = t + rnd.uniform(0, 86400)
                it = rnd.choices(types, weights)[0]
                fat = rnd.randint(1, 12) if it in ("killing", "armed_attack") and rnd.random() < 0.7 else 0
                rows.append((ts, name, lat + rnd.uniform(-0.06, 0.06), lon + rnd.uniform(-0.06, 0.06), it,
                             core.INCIDENT_TYPES[it][1], fat, "synthetic history", "synthetic", None, None,
                             1 if rnd.random() < 0.8 else 0, 0.6))
                if core.INCIDENT_TYPES[it][1] >= 2:
                    recent.append(ts)
            t += 86400
    core.xmany(cfg, "INSERT INTO incidents(ts, lga, lat, lon, type, severity, fatalities, description, source, "
                    "reporter_hash, reporter_enc, verified, credibility) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    print(f"Generated {len(rows)} synthetic incidents over {a.weeks} weeks for {len(geodata.LGAS)} LGAs.")


def _poisson(rnd, lam):
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= l:
            return k
        k += 1


def cmd_import_acled(a):
    """Import an ACLED CSV export (acleddata.com, free account). Keeps Nigerian events whose
    notes or actors mention herders/pastoralists/farmers and maps them to the nearest LGA."""
    cfg = core.load_config()
    keep = ("herder", "herdsmen", "fulani", "pastoral", "cattle", "farmer", "grazing")
    n = skipped = 0
    with open(a.csv, encoding="utf-8", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            if r.get("country") and r["country"] != "Nigeria":
                continue
            text = " ".join([r.get("notes", ""), r.get("actor1", ""), r.get("actor2", "")]).lower()
            if not any(k in text for k in keep):
                continue
            try:
                lat, lon = float(r["latitude"]), float(r["longitude"])
                ts = datetime.strptime(r["event_date"][:10], "%Y-%m-%d").timestamp() \
                    if "-" in r["event_date"] else datetime.strptime(r["event_date"], "%d %B %Y").timestamp()
            except (ValueError, KeyError):
                skipped += 1
                continue
            lga = core.nearest_lga(cfg, lat, lon, max_km=a.max_km)
            if not lga:
                skipped += 1
                continue
            fat = int(r.get("fatalities") or 0)
            et = (r.get("sub_event_type") or r.get("event_type") or "").lower()
            itype = "killing" if fat > 0 else "armed_attack" if "attack" in et or "armed" in et else \
                "displacement" if "displace" in et else "threat"
            core.add_incident(cfg, lga, itype, r.get("notes", "")[:500], "acled", lat, lon, None, fat, 1, ts)
            n += 1
    print(f"Imported {n} ACLED events, skipped {skipped}.")


def build_dataset(cfg, horizon_days=7, step_days=7):
    """Weekly panel: features at time t, label = any serious incident in (t, t+horizon]."""
    inc = core.q(cfg, "SELECT ts, lga, type, severity, fatalities, verified FROM incidents ORDER BY ts")
    if not inc:
        raise SystemExit("No incidents. Run `python manage.py history` or import ACLED data first.")
    ndvi = {(r["lga"], r["year"], r["month"]): r["value"] - r["clim"] for r in core.q(cfg, "SELECT * FROM ndvi")}
    base = {l["name"]: l["baseline"] for l in core.q(cfg, "SELECT * FROM lgas")}
    by_lga = {}
    for r in inc:
        by_lga.setdefault(r["lga"], []).append(r)
    t0, t1 = inc[0]["ts"] + 30 * 86400, time.time() - horizon_days * 86400
    X, y, T = [], [], []
    for lga, rows in by_lga.items():
        t = t0
        while t < t1:
            hist = [r for r in rows if t - 30 * 86400 <= r["ts"] <= t]
            f = core.lga_features(cfg, lga, t, hist, ndvi, base.get(lga, 0.3))
            label = any(t < r["ts"] <= t + horizon_days * 86400 and r["severity"] >= 2 for r in rows)
            X.append([f[k] for k in core.FEATURES])
            y.append(int(label))
            T.append(t)
            t += step_days * 86400
    return X, y, T


def cmd_train(a):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    cfg = core.load_config()
    X, y, T = build_dataset(cfg)
    order = sorted(range(len(T)), key=lambda i: T[i])
    cut = int(len(order) * 0.8)  # time-based split: train on the past, test on the most recent 20%
    tr, te = order[:cut], order[cut:]
    Xtr, ytr = [X[i] for i in tr], [y[i] for i in tr]
    Xte, yte = [X[i] for i in te], [y[i] for i in te]
    models = {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000,
                                                                                  class_weight="balanced")),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                                random_state=42, n_jobs=-1),
    }
    results = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        pred = [int(v >= 0.5) for v in p]
        results[name] = {"auc": round(roc_auc_score(yte, p), 3), "precision": round(precision_score(yte, pred), 3),
                         "recall": round(recall_score(yte, pred), 3), "f1": round(f1_score(yte, pred), 3),
                         "brier": round(brier_score_loss(yte, p), 3)}
    # Naive comparator used by many humanitarian dashboards: "last month's incident count".
    i30 = core.FEATURES.index("inc30")
    results["naive_baseline_inc30"] = {"auc": round(roc_auc_score(yte, [r[i30] for r in Xte]), 3)}
    best = max((k for k in results if k in models), key=lambda k: results[k]["auc"])
    importances = {}
    if hasattr(models["random_forest"], "feature_importances_"):
        importances = dict(zip(core.FEATURES, [round(v, 3) for v in models["random_forest"].feature_importances_]))
    blob = pickle.dumps({"model": models[best], "name": best, "features": core.FEATURES,
                         "trained": datetime.now().isoformat(timespec="seconds")})
    with open(cfg["model_path"], "wb") as fh:
        fh.write(blob)
    with open(cfg["model_path"] + ".sha256", "w") as fh:
        fh.write(hashlib.sha256(blob).hexdigest())
    summary = {"samples": len(y), "positives": sum(y), "train": len(tr), "test": len(te), "models": results,
               "selected": best, "rf_feature_importance": importances}
    with open(os.path.join(os.path.dirname(cfg["model_path"]), "model_metrics.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    core.audit(cfg, "cli", "train_model", f"{best} auc={results[best]['auc']}")
    print(json.dumps(summary, indent=2))


def cmd_risk(a):
    cfg = core.load_config()
    for r in core.compute_risk(cfg)[: a.top]:
        print(f"{r['score']:5.1f} {r['level']:9s} {r['lga']:22s} {r['state']:9s} "
              f"rule={r['rule_score']:5.1f} ml={'-' if r['ml_prob'] is None else round(r['ml_prob'], 2)} "
              f"| {', '.join(d[0] for d in r['drivers'][:2])}")


def main():
    p = argparse.ArgumentParser(description="AgroPeace management")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("genkey", help="generate encryption and signing keys").set_defaults(fn=cmd_genkey)
    s.add_parser("init", help="create database, geography, NDVI, contacts, users").set_defaults(fn=cmd_init)
    h = s.add_parser("history", help="generate synthetic incident history for training")
    h.add_argument("--weeks", type=int, default=104)
    h.add_argument("--seed", type=int, default=2026)
    h.set_defaults(fn=cmd_history)
    i = s.add_parser("import-acled", help="import real ACLED events from a CSV export")
    i.add_argument("csv")
    i.add_argument("--max-km", type=float, default=40)
    i.set_defaults(fn=cmd_import_acled)
    s.add_parser("train", help="train and evaluate the risk model").set_defaults(fn=cmd_train)
    r = s.add_parser("risk", help="print current risk ranking")
    r.add_argument("--top", type=int, default=10)
    r.set_defaults(fn=cmd_risk)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
