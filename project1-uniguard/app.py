"""UniGuard web dashboard and scheduler.

Run:  python app.py      then open http://127.0.0.1:5000
"""
import functools
import os
import secrets
import threading
import time

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for

import backup_engine
import monitor
import ransomware_guard
from common import audit, check_password, db_exec, db_query, load_config, log, verify_audit_chain

cfg = load_config()
app = Flask(__name__)
app.secret_key = os.environ.get(cfg["dashboard"]["secret_key_env"]) or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                  PERMANENT_SESSION_LIFETIME=1800)

_failed = {}


def login_required(role=None):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            if "user" not in session:
                return redirect(url_for("login", next=request.path))
            if role and session.get("role") != role:
                abort(403)
            if request.method == "POST" and request.form.get("csrf") != session.get("csrf"):
                abort(400)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject():
    return {"institution": cfg["institution"], "csrf": session.get("csrf", ""), "user": session.get("user"),
            "role": session.get("role"), "fmt": lambda ts: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr
        fails = [t for t in _failed.get(ip, []) if time.time() - t < 300]
        if len(fails) >= 5:  # brute-force lockout: 5 failures per 5 minutes
            flash("Too many failed attempts. Wait 5 minutes.")
            return render_template("login.html"), 429
        u = request.form.get("username", "")
        users = load_config()["users"]
        if u in users and check_password(request.form.get("password", ""), users[u]["password"]):
            session.clear()
            session.update(user=u, role=users[u]["role"], csrf=secrets.token_hex(16))
            audit(cfg, u, "login", ip)
            return redirect(request.args.get("next") or url_for("index"))
        _failed[ip] = fails + [time.time()]
        audit(cfg, u or "?", "login_failed", ip)
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    audit(cfg, session.get("user", "?"), "logout", "")
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required()
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
@login_required()
def api_status():
    latest = {}
    for r in db_query(cfg, "SELECT name, value, MAX(ts) AS ts FROM metrics GROUP BY name"):
        latest[r["name"]] = r["value"]
    services = db_query(cfg, "SELECT service, ok, latency_ms, detail, MAX(ts) AS ts FROM service_checks "
                             "GROUP BY service")
    since = time.time() - 3600
    series = db_query(cfg, "SELECT ts, name, value FROM metrics WHERE ts > ? AND name IN "
                           "('cpu_percent','memory_percent') ORDER BY ts", (since,))
    alerts = db_query(cfg, "SELECT * FROM alerts ORDER BY id DESC LIMIT 15")
    backups = db_query(cfg, "SELECT * FROM backups ORDER BY id DESC LIMIT 8")
    restores = db_query(cfg, "SELECT * FROM restores ORDER BY id DESC LIMIT 5")
    age = backup_engine.last_backup_age_minutes(cfg)
    uptime = db_query(cfg, "SELECT service, AVG(ok)*100 AS pct FROM service_checks WHERE ts > ? "
                           "GROUP BY service", (time.time() - 86400,))
    return jsonify(latest=latest, services=services, series=series, alerts=alerts, backups=backups,
                   restores=restores, backup_age_min=age, rpo=cfg["backup"]["rpo_minutes"],
                   canary=ransomware_guard.check_canaries(cfg), uptime=uptime,
                   open_alerts=db_query(cfg, "SELECT COUNT(*) AS n FROM alerts WHERE acknowledged=0 "
                                             "AND severity!='info'")[0]["n"])


@app.route("/snapshots")
@login_required()
def snapshots():
    keys = backup_engine.load_keys(cfg)
    snaps = []
    for sid in reversed(backup_engine.list_snapshots(cfg)):
        m = backup_engine.load_snapshot(cfg, keys, sid)
        snaps.append({"id": sid, "created": m["created"], "files": len(m["files"]),
                      "size": sum(f["size"] for f in m["files"])})
    return render_template("snapshots.html", snaps=snaps)


@app.route("/action/<name>", methods=["POST"])
@login_required(role="admin")
def action(name):
    user = session["user"]
    try:
        if name == "backup":
            r = backup_engine.run_backup(cfg, actor=user)
            flash(f"Backup: {r['status']} {r.get('snapshot', '')}")
        elif name == "verify":
            r = backup_engine.verify_repository(cfg, actor=user)
            flash("Verification passed: %d objects checked" % r["objects_checked"] if r["ok"]
                  else "Verification FAILED: " + "; ".join(r["problems"][:3]))
        elif name == "restore":
            sid = request.form["snapshot"]
            target = request.form.get("target") or None
            r = backup_engine.restore(cfg, sid, target, request.form.get("prefix", ""), actor=user)
            if not target:
                backup_engine.remove_attack_leftovers(cfg)
                ransomware_guard.deploy_canaries(cfg)
            flash(f"Restored {r['files']} files from {r['snapshot']} in {r['duration_s']}s")
        elif name == "ack":
            db_exec(cfg, "UPDATE alerts SET acknowledged=1 WHERE acknowledged=0")
            audit(cfg, user, "ack_alerts", "")
            flash("All alerts acknowledged.")
        elif name == "prune":
            r = backup_engine.prune(cfg, actor=user)
            flash(f"Pruned {len(r['removed_snapshots'])} snapshots, {r['gc_objects']} objects")
        else:
            abort(404)
    except Exception as exc:
        flash(f"Error: {exc}")
        log(cfg, f"dashboard action {name} failed: {exc}")
    return redirect(request.referrer or url_for("index"))


@app.route("/audit")
@login_required()
def audit_page():
    rows = db_query(cfg, "SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")
    ok, bad = verify_audit_chain(cfg)
    return render_template("audit.html", rows=rows, chain_ok=ok, bad=bad)


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# ---------------------------------------------------------------- scheduler

def _loop(name, interval, fn):
    while True:
        try:
            fn()
        except SystemExit as exc:
            log(cfg, f"{name}: {exc}")
        except Exception as exc:
            log(cfg, f"{name} error: {exc}")
        time.sleep(interval)


def start_scheduler():
    threading.Thread(target=_loop, args=("monitor", cfg["monitor"]["interval_seconds"],
                                         lambda: monitor.run_once(cfg)), daemon=True).start()
    threading.Thread(target=_loop, args=("backup", cfg["backup"]["interval_minutes"] * 60,
                                         lambda: backup_engine.run_backup(cfg)), daemon=True).start()
    threading.Thread(target=_loop, args=("verify", 6 * 3600,
                                         lambda: backup_engine.verify_repository(cfg)), daemon=True).start()
    threading.Thread(target=_loop, args=("prune", 24 * 3600,
                                         lambda: backup_engine.prune(cfg)), daemon=True).start()


if __name__ == "__main__":
    if not os.path.exists(os.path.join(cfg["backup"]["repository"], backup_engine.KEYINFO)):
        raise SystemExit("Run `python cli.py init` first.")
    start_scheduler()
    log(cfg, f"UniGuard dashboard on http://{cfg['dashboard']['host']}:{cfg['dashboard']['port']}")
    app.run(host=cfg["dashboard"]["host"], port=cfg["dashboard"]["port"], debug=False, use_reloader=False)
