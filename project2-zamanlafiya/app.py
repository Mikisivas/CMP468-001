"""Zaman Lafiya web application: live GIS dashboard, incident intake (web, SMS, USSD),
herd GPS ingestion with geofencing, case management for mediation, and alerting.

Run:  python app.py   then open http://127.0.0.1:5050
"""
import functools
import json
import os
import secrets
import threading
import time

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for

import core

cfg = core.load_config()
app = Flask(__name__)
app.secret_key = os.environ.get(cfg["security"]["secret_key_env"]) or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=3600,
                  MAX_CONTENT_LENGTH=64 * 1024)

ROLE_RANK = {"viewer": 0, "responder": 1, "analyst": 2, "admin": 3}
_state = {"risks": [], "ts": 0}
_hits = {}


def require(min_role="viewer"):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            if "user" not in session:
                return redirect(url_for("login", next=request.path))
            if ROLE_RANK[session["role"]] < ROLE_RANK[min_role]:
                abort(403)
            if request.method == "POST" and request.form.get("csrf") != session.get("csrf"):
                abort(400)
            return fn(*a, **kw)
        return wrapper
    return deco


def rate_limited(bucket, limit, window=60):
    key = (bucket, request.remote_addr)
    hits = [t for t in _hits.get(key, []) if time.time() - t < window]
    _hits[key] = hits + [time.time()]
    return len(hits) >= limit


@app.context_processor
def ctx():
    return {"user": session.get("user"), "role": session.get("role"), "csrf": session.get("csrf", ""),
            "rank": ROLE_RANK.get(session.get("role"), -1), "types": core.INCIDENT_TYPES,
            "fmt": lambda ts: time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))}


@app.after_request
def sec_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp


# ---------------------------------------------------------------- auth

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if rate_limited("login", 5, 300):
            flash("Too many attempts. Try again in 5 minutes.")
            return render_template("login.html"), 429
        u = request.form.get("username", "")
        row = core.q(cfg, "SELECT * FROM users WHERE username=?", (u,))
        if row and core.check_password(request.form.get("password", ""), row[0]["password"]):
            session.clear()
            session.update(user=u, role=row[0]["role"], csrf=secrets.token_hex(16))
            core.audit(cfg, u, "login", request.remote_addr)
            return redirect(request.args.get("next") or url_for("index"))
        core.audit(cfg, u or "?", "login_failed", request.remote_addr)
        flash("Invalid credentials.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    core.audit(cfg, session.get("user", "?"), "logout")
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- dashboard

@app.route("/")
@require()
def index():
    return render_template("map.html")


@app.route("/api/state")
@require()
def api_state():
    since = time.time() - 14 * 86400
    incidents = core.q(cfg, "SELECT id, ts, lga, lat, lon, type, severity, fatalities, source, verified "
                            "FROM incidents WHERE ts > ? AND source != 'synthetic' ORDER BY ts DESC LIMIT 300",
                       (since,))
    hist = core.q(cfg, "SELECT lat, lon, severity FROM incidents WHERE ts > ? AND type!='rumour'",
                  (time.time() - 90 * 86400,))
    herds = core.q(cfg, "SELECT herd_id, lat, lon, heads, MAX(ts) AS ts FROM herd_pings WHERE ts > ? "
                        "GROUP BY herd_id", (time.time() - 6 * 3600,))
    trails = {}
    for p in core.q(cfg, "SELECT herd_id, lat, lon FROM herd_pings WHERE ts > ? ORDER BY ts",
                    (time.time() - 3 * 3600,)):
        trails.setdefault(p["herd_id"], []).append([p["lat"], p["lon"]])
    alerts = core.q(cfg, "SELECT id, ts, lga, level, kind, message, recipients FROM alerts ORDER BY id DESC LIMIT 25")
    cases = core.q(cfg, "SELECT status, COUNT(*) AS n FROM cases GROUP BY status")
    return jsonify(risks=_state["risks"], risk_ts=_state["ts"], incidents=incidents, history=hist, herds=herds,
                   trails=trails, alerts=alerts, cases=cases)


@app.route("/api/zones")
@require()
def api_zones():
    feats = [{"type": "Feature", "geometry": z["geom"],
              "properties": {"kind": z["kind"], "name": z["name"], "lga": z["lga"]}} for z in core.zones(cfg)]
    return jsonify({"type": "FeatureCollection", "features": feats})


@app.route("/api/lga/<name>/trend")
@require()
def lga_trend(name):
    rows = core.q(cfg, "SELECT ts, score FROM risk_scores WHERE lga=? ORDER BY ts DESC LIMIT 120", (name,))
    return jsonify(list(reversed(rows)))


# ---------------------------------------------------------------- intake: web form (public)

@app.route("/report", methods=["GET", "POST"])
def report():
    lgas = [l["name"] for l in core.q(cfg, "SELECT name FROM lgas ORDER BY name")]
    if request.method == "POST":
        if rate_limited("report", 10, 600):
            abort(429)
        if request.form.get("website"):  # honeypot field: bots fill it, people never see it
            abort(400)
        try:
            lat = float(request.form["lat"]) if request.form.get("lat") else None
            lon = float(request.form["lon"]) if request.form.get("lon") else None
            if lat is not None and not (4 <= lat <= 14 and 2.5 <= lon <= 15):
                raise ValueError("coordinates outside Nigeria")
            phone = None if request.form.get("anonymous") else (request.form.get("phone") or None)
            iid = core.add_incident(cfg, request.form["lga"], request.form["type"],
                                    request.form.get("description", ""), "web", lat, lon, phone,
                                    int(request.form.get("fatalities") or 0))
            flash(f"Thank you. Report #{iid} received. Your identity is protected.")
            return redirect(url_for("report"))
        except (ValueError, KeyError, PermissionError) as exc:
            flash(f"Report not accepted: {exc}")
    return render_template("report.html", lgas=lgas)


# ---------------------------------------------------------------- intake: SMS and USSD gateways

@app.route("/api/sms", methods=["POST"])
def api_sms():
    """Inbound SMS webhook (Africa's Talking style form fields: from, text)."""
    if rate_limited("sms", 60):
        abort(429)
    phone, text = request.form.get("from", ""), request.form.get("text", "")
    parsed = core.parse_sms(text)
    if not parsed:
        return "Format: ZL <LGA> <CROP|RUSTLE|COW|THREAT|RUMOUR|ROUTE|ATTACK|KILL|FLEE> <details>", 200
    lga = core.resolve_lga_name(cfg, parsed["lga"])
    if not lga:
        return f"Unknown LGA '{parsed['lga']}'. Example: ZL Guma CROP cows in yam farm", 200
    try:
        iid = core.add_incident(cfg, lga, parsed["type"], parsed["description"], "sms", phone=phone)
    except PermissionError:
        return "Too many reports from this number. Please call the peace committee.", 200
    return f"Zaman Lafiya: report #{iid} received for {lga}. Stay safe.", 200


@app.route("/api/ussd", methods=["POST"])
def api_ussd():
    """USSD menu for basic phones (Africa's Talking style: sessionId, phoneNumber, text)."""
    phone, text = request.form.get("phoneNumber", ""), request.form.get("text", "")
    steps = [s for s in text.split("*")] if text else []
    types = list(core.INCIDENT_TYPES)
    if not steps:
        return "CON Zaman Lafiya\n1. Report incident\n2. Check risk in my LGA"
    if steps[0] == "2":
        if len(steps) == 1:
            return "CON Enter your LGA name:"
        lga = core.resolve_lga_name(cfg, steps[1])
        r = next((r for r in _state["risks"] if r["lga"] == lga), None)
        return f"END {lga}: risk {r['level']} ({r['score']:.0f}/100)" if r else "END LGA not found."
    if steps[0] == "1":
        if len(steps) == 1:
            return "CON Enter your LGA name:"
        lga = core.resolve_lga_name(cfg, steps[1])
        if not lga:
            return "END LGA not found. Dial again."
        if len(steps) == 2:
            menu = "\n".join(f"{i + 1}. {core.INCIDENT_TYPES[t][0]}" for i, t in enumerate(types))
            return "CON What happened?\n" + menu
        try:
            itype = types[int(steps[2]) - 1]
        except (ValueError, IndexError):
            return "END Invalid choice."
        iid = core.add_incident(cfg, lga, itype, "via USSD", "ussd", phone=phone)
        return f"END Report #{iid} received. Help is being informed. Stay safe."
    return "END Invalid choice."


# ---------------------------------------------------------------- intake: herd GPS devices

@app.route("/api/herd_ping", methods=["POST"])
def herd_ping():
    """GPS pings from herder phones or collars. Signed with HMAC-SHA256 and a timestamp
    so pings cannot be forged or replayed."""
    secret = os.environ.get(cfg["security"]["device_secret_env"], "")
    body = request.get_data()
    ts = request.headers.get("X-Timestamp", "0")
    sig = request.headers.get("X-Signature", "")
    if not secret or abs(time.time() - float(ts or 0)) > 300:
        abort(401)
    if not core.hmac.compare_digest(sig, core.device_signature(secret, ts.encode() + b"." + body)):
        core.audit(cfg, "device", "bad_signature", request.remote_addr)
        abort(401)
    d = json.loads(body)
    lat, lon = float(d["lat"]), float(d["lon"])
    if not (4 <= lat <= 14 and 2.5 <= lon <= 15):
        abort(400)
    core.x(cfg, "INSERT INTO herd_pings(ts, herd_id, lat, lon, heads) VALUES (?,?,?,?,?)",
           (time.time(), str(d["herd_id"])[:32], lat, lon, int(d.get("heads", 0))))
    return jsonify(events=core.check_geofence(cfg, str(d["herd_id"])[:32], lat, lon))


# ---------------------------------------------------------------- analyst & responder pages

@app.route("/incidents")
@require("analyst")
def incidents():
    rows = core.q(cfg, "SELECT * FROM incidents WHERE source!='synthetic' ORDER BY id DESC LIMIT 200")
    for r in rows:
        r["reporter"] = "anonymous" if not r["reporter_enc"] else "protected (encrypted)"
    return render_template("incidents.html", rows=rows)


@app.route("/incidents/<int:iid>/<verdict>", methods=["POST"])
@require("analyst")
def verify_incident(iid, verdict):
    core.set_verification(cfg, iid, verdict == "confirm", session["user"])
    flash(f"Incident #{iid} {'confirmed' if verdict == 'confirm' else 'rejected as false'}.")
    return redirect(url_for("incidents"))


@app.route("/incidents/<int:iid>/reveal", methods=["POST"])
@require("admin")
def reveal(iid):
    """Need-to-know access to a reporter's number, always written to the audit log."""
    r = core.q(cfg, "SELECT reporter_enc FROM incidents WHERE id=?", (iid,))
    core.audit(cfg, session["user"], "reveal_reporter", f"incident={iid} reason={request.form.get('reason', '')}")
    flash(f"Reporter for #{iid}: {core.decrypt_pii(cfg, r[0]['reporter_enc']) if r and r[0]['reporter_enc'] else 'anonymous'}"
          " (access logged)")
    return redirect(url_for("incidents"))


@app.route("/cases", methods=["GET", "POST"])
@require("responder")
def cases():
    if request.method == "POST":
        cid = int(request.form["id"])
        status = request.form["status"]
        if status not in ("reported", "verified", "mediation_scheduled", "in_mediation", "resolved", "escalated"):
            abort(400)
        core.x(cfg, "UPDATE cases SET status=?, mediator=?, notes=?, compensation_ngn=?, updated=? WHERE id=?",
               (status, request.form.get("mediator", "")[:120], request.form.get("notes", "")[:1000],
                float(request.form.get("compensation") or 0), time.time(), cid))
        core.audit(cfg, session["user"], "update_case", f"case={cid} status={status}")
        flash(f"Case #{cid} updated.")
        return redirect(url_for("cases"))
    rows = core.q(cfg, "SELECT c.*, i.type, i.description, i.ts AS inc_ts FROM cases c "
                       "LEFT JOIN incidents i ON i.id=c.incident_id ORDER BY c.id DESC LIMIT 100")
    return render_template("cases.html", rows=rows)


@app.route("/audit")
@require("admin")
def audit_page():
    ok, bad = core.verify_audit(cfg)
    rows = core.q(cfg, "SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")
    return render_template("audit.html", rows=rows, ok=ok, bad=bad)


# ---------------------------------------------------------------- scheduler

def risk_loop():
    while True:
        try:
            risks = core.compute_risk(cfg)
            _state.update(risks=risks, ts=time.time())
            core.evaluate_alerts(cfg, risks)
        except Exception as exc:
            print("risk loop error:", exc, flush=True)
        time.sleep(cfg["risk_interval_seconds"])


if __name__ == "__main__":
    if not os.path.exists(cfg["database"]):
        raise SystemExit("Run `python manage.py init` first.")
    threading.Thread(target=risk_loop, daemon=True).start()
    print(f"Zaman Lafiya on http://{cfg['dashboard']['host']}:{cfg['dashboard']['port']}  "
          f"(public report form at /report)")
    app.run(host=cfg["dashboard"]["host"], port=cfg["dashboard"]["port"], debug=False, use_reloader=False)
