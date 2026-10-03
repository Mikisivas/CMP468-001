"""Shared helpers for UniGuard: config, database, audit log and alert dispatch."""
import hashlib
import json
import os
import smtplib
import sqlite3
import ssl
import threading
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("UNIGUARD_CONFIG", os.path.join(BASE_DIR, "config.json"))

_db_lock = threading.Lock()


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    # Resolve relative paths against the project folder so the tool runs from anywhere.
    for key in ("database", "log_file"):
        cfg[key] = _abs(cfg[key])
    b = cfg["backup"]
    b["repository"] = _abs(b["repository"])
    b["sources"] = [_abs(p) for p in b["sources"]]
    b["replicas"] = [dict(r, path=_abs(r["path"])) for r in b.get("replicas", [])]
    cfg["ransomware_guard"]["canary_dir"] = _abs(cfg["ransomware_guard"]["canary_dir"])
    return cfg


def save_config(cfg_raw):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg_raw, fh, indent=2)


def _abs(path):
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(BASE_DIR, path))


# ---------------------------------------------------------------- database

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    ts REAL, host TEXT, name TEXT, value REAL);
CREATE INDEX IF NOT EXISTS idx_metrics ON metrics(name, ts);
CREATE TABLE IF NOT EXISTS service_checks (
    ts REAL, service TEXT, ok INTEGER, latency_ms REAL, detail TEXT);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, severity TEXT,
    source TEXT, message TEXT, alert_key TEXT, acknowledged INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, snapshot_id TEXT, status TEXT,
    files INTEGER, new_objects INTEGER, bytes_in INTEGER, bytes_stored INTEGER,
    duration_s REAL, detail TEXT);
CREATE TABLE IF NOT EXISTS restores (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, snapshot_id TEXT, target TEXT,
    files INTEGER, duration_s REAL, verified INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, action TEXT,
    detail TEXT, prev_hash TEXT, entry_hash TEXT);
"""


def db_connect(cfg):
    conn = sqlite3.connect(cfg["database"], timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def db_exec(cfg, sql, params=()):
    with _db_lock:
        conn = db_connect(cfg)
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def db_query(cfg, sql, params=()):
    with _db_lock:
        conn = db_connect(cfg)
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()


# ---------------------------------------------------------------- audit trail

def audit(cfg, actor, action, detail=""):
    """Append a tamper-evident audit entry. Each entry hashes the previous one."""
    last = db_query(cfg, "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    prev_hash = last[0]["entry_hash"] if last else "GENESIS"
    ts = time.time()
    entry_hash = hashlib.sha256(f"{prev_hash}|{ts}|{actor}|{action}|{detail}".encode()).hexdigest()
    db_exec(cfg, "INSERT INTO audit_log(ts, actor, action, detail, prev_hash, entry_hash) "
                 "VALUES (?,?,?,?,?,?)", (ts, actor, action, detail, prev_hash, entry_hash))


def verify_audit_chain(cfg):
    rows = db_query(cfg, "SELECT * FROM audit_log ORDER BY id")
    prev = "GENESIS"
    for r in rows:
        expect = hashlib.sha256(
            f"{prev}|{r['ts']}|{r['actor']}|{r['action']}|{r['detail']}".encode()).hexdigest()
        if r["prev_hash"] != prev or r["entry_hash"] != expect:
            return False, r["id"]
        prev = r["entry_hash"]
    return True, None


# ---------------------------------------------------------------- logging

def log(cfg, message):
    line = time.strftime("%Y-%m-%d %H:%M:%S") + "  " + message
    print(line, flush=True)
    with open(cfg["log_file"], "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------- alerting

_last_sent = {}


def raise_alert(cfg, severity, source, message, alert_key=None):
    """Store an alert and push it to every enabled channel.

    alert_key de-duplicates repeated alerts inside the cooldown window, which
    stops one failing service from flooding the ICT team's phones.
    """
    key = alert_key or f"{source}:{message}"
    cooldown = cfg["alerts"].get("cooldown_seconds", 600)
    now = time.time()
    if key in _last_sent and now - _last_sent[key] < cooldown:
        return False
    _last_sent[key] = now
    db_exec(cfg, "INSERT INTO alerts(ts, severity, source, message, alert_key) VALUES (?,?,?,?,?)",
            (now, severity, source, message, key))
    text = f"[UniGuard {severity.upper()}] {cfg['institution']} | {source}: {message}"
    log(cfg, text)
    channels = cfg["alerts"]["channels"]
    for name, sender in (("email", _send_email), ("telegram", _send_telegram), ("sms", _send_sms)):
        ch = channels.get(name, {})
        if ch.get("enabled") and severity in ch.get("severities", ["critical", "warning"]):
            threading.Thread(target=_safe_send, args=(cfg, sender, ch, text), daemon=True).start()
    return True


def _safe_send(cfg, sender, ch, text):
    try:
        sender(ch, text)
    except Exception as exc:  # a broken channel must never stop monitoring
        log(cfg, f"alert channel error: {exc}")


def _send_email(ch, text):
    msg = EmailMessage()
    msg["Subject"] = text[:120]
    msg["From"] = ch["from"]
    msg["To"] = ", ".join(ch["to"])
    msg.set_content(text)
    with smtplib.SMTP(ch["smtp_host"], ch.get("smtp_port", 587), timeout=15) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(ch["username"], os.environ.get(ch.get("password_env", "UNIGUARD_SMTP_PASSWORD"), ""))
        s.send_message(msg)


def _send_telegram(ch, text):
    token = os.environ.get(ch.get("token_env", "UNIGUARD_TELEGRAM_TOKEN"), "")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": ch["chat_id"], "text": text}).encode()
    urllib.request.urlopen(url, data=data, timeout=15).read()


def _send_sms(ch, text):
    """Generic SMS gateway webhook (works with Termii or Africa's Talking style APIs)."""
    payload = json.dumps({"to": ch["to"], "sms": text[:300], "from": ch.get("sender_id", "UniGuard"),
                          "api_key": os.environ.get(ch.get("api_key_env", "UNIGUARD_SMS_KEY"), "")}).encode()
    req = urllib.request.Request(ch["url"], data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


# ---------------------------------------------------------------- passwords

def hash_password(password, salt=None, iterations=310_000):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def check_password(password, stored):
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac_compare(test, digest)


def hmac_compare(a, b):
    import hmac
    return hmac.compare_digest(a, b)
