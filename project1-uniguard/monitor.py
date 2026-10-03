"""Host and service monitoring with static thresholds, adaptive anomaly
detection, backup freshness (RPO) checks and simple self-healing."""
import shlex
import socket
import statistics
import subprocess
import sys
import time
import urllib.request

import psutil

import ransomware_guard
from backup_engine import last_backup_age_minutes
from common import BASE_DIR, audit, db_exec, db_query, log, raise_alert


def collect_host_metrics(cfg):
    m = cfg["monitor"]
    vals = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
    }
    for path in m.get("disk_paths", ["/"]):
        try:
            vals[f"disk_percent:{path}"] = psutil.disk_usage(path).percent
        except (FileNotFoundError, PermissionError):
            pass
    net = psutil.net_io_counters()
    vals["net_sent_mb"] = round(net.bytes_sent / 1e6, 2)
    vals["net_recv_mb"] = round(net.bytes_recv / 1e6, 2)
    # Power matters in Nigeria: a server on UPS/inverter battery is an early warning.
    batt = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if batt is not None:
        vals["battery_percent"] = batt.percent
        vals["on_mains_power"] = 1.0 if batt.power_plugged else 0.0
    return vals


def check_service(svc):
    start = time.time()
    try:
        if svc["type"] == "http":
            with urllib.request.urlopen(svc["url"], timeout=svc.get("timeout", 5)) as r:
                ok = 200 <= r.status < 400
                detail = f"HTTP {r.status}"
        elif svc["type"] == "tcp":
            with socket.create_connection((svc["host"], svc["port"]), timeout=svc.get("timeout", 5)):
                ok, detail = True, "port open"
        else:
            ok, detail = False, "unknown check type"
    except Exception as exc:
        ok, detail = False, type(exc).__name__ + ": " + str(exc)[:120]
    return ok, round((time.time() - start) * 1000, 1), detail


def _zscore_anomaly(cfg, name, value):
    """Flag values far outside the recent sliding window (mean +/- z*stdev)."""
    window = cfg["monitor"].get("anomaly_window", 30)
    rows = db_query(cfg, "SELECT value FROM metrics WHERE name=? ORDER BY ts DESC LIMIT ?", (name, window))
    hist = [r["value"] for r in rows]
    if len(hist) < max(10, window // 2):
        return None
    mean = statistics.fmean(hist)
    sd = statistics.pstdev(hist)
    if sd < 1.0:  # ignore near-flat metrics; tiny wobbles are not incidents
        return None
    z = (value - mean) / sd
    return z if abs(z) >= cfg["monitor"].get("anomaly_z", 3.0) else None


def _run_remediation(cfg, svc):
    cmd = svc.get("restart_command")
    if not cmd:
        return False
    parts = shlex.split(cmd)
    if parts and parts[0] in ("python", "python3"):
        parts[0] = sys.executable
    try:
        subprocess.Popen(parts, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audit(cfg, "auto-remediation", "restart_service", svc["name"])
        log(cfg, f"Self-healing: restart command issued for {svc['name']}")
        return True
    except Exception as exc:
        log(cfg, f"Self-healing failed for {svc['name']}: {exc}")
        return False


_down_since = {}


def run_once(cfg):
    now = time.time()
    host = cfg["host_name"]
    th = cfg["monitor"]["thresholds"]
    vals = collect_host_metrics(cfg)
    for name, value in vals.items():
        base = name.split(":")[0]
        if base in th and base != "battery_percent" and value >= th[base]:
            raise_alert(cfg, "warning", "Host", f"{name} at {value:.1f}% (threshold {th[base]}%)", f"th:{name}")
        z = _zscore_anomaly(cfg, name, value) if base in ("cpu_percent", "memory_percent") else None
        if z is not None:
            raise_alert(cfg, "warning", "Anomaly", f"{name}={value:.1f} is {z:+.1f} std devs from normal",
                        f"z:{name}")
        db_exec(cfg, "INSERT INTO metrics(ts, host, name, value) VALUES (?,?,?,?)", (now, host, name, value))
    if vals.get("on_mains_power") == 0.0 and vals.get("battery_percent", 100) <= th.get("battery_percent", 30):
        raise_alert(cfg, "critical", "Power",
                    f"Server on battery at {vals['battery_percent']:.0f}%. Run an emergency backup "
                    f"and plan graceful shutdown.", "power")

    results = []
    for svc in cfg["monitor"]["services"]:
        ok, latency, detail = check_service(svc)
        db_exec(cfg, "INSERT INTO service_checks(ts, service, ok, latency_ms, detail) VALUES (?,?,?,?,?)",
                (now, svc["name"], int(ok), latency, detail))
        if ok:
            if svc["name"] in _down_since:
                outage = now - _down_since.pop(svc["name"])
                raise_alert(cfg, "info", "Service", f"{svc['name']} recovered after {outage:.0f}s",
                            f"up:{svc['name']}:{int(now)}")
        else:
            first = svc["name"] not in _down_since
            _down_since.setdefault(svc["name"], now)
            raise_alert(cfg, "critical", "Service", f"{svc['name']} is DOWN ({detail})", f"down:{svc['name']}")
            if first:
                _run_remediation(cfg, svc)
        results.append({"service": svc["name"], "ok": ok, "latency_ms": latency, "detail": detail})

    age = last_backup_age_minutes(cfg)
    rpo = cfg["backup"]["rpo_minutes"]
    if age is None or age > rpo:
        raise_alert(cfg, "warning", "Backup",
                    "No successful backup yet" if age is None else
                    f"Last good backup is {age:.0f} min old (RPO target {rpo} min)", "rpo")

    guard = ransomware_guard.check_canaries(cfg)
    if guard["tripped"]:
        raise_alert(cfg, "critical", "Ransomware Guard",
                    "Canary files modified or deleted: " + ", ".join(guard["changed"]) +
                    ". Isolate the server and restore from the last clean snapshot.", "canary")
    return {"metrics": vals, "services": results, "backup_age_min": age, "canary": guard}
