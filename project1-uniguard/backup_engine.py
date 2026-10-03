"""Encrypted, de-duplicated, tamper-evident backup and recovery engine.

Design (maps to CMP 468 topics):
  * Confidentiality: every object is compressed then sealed with AES-256-GCM.
  * Integrity: object ids are HMAC-SHA256 tags of the plaintext, GCM tags detect
    tampering, and every snapshot manifest stores the hash of the previous one
    (a hash chain, so a deleted or edited snapshot is detected).
  * Availability: 3-2-1 copies (repository + NAS replica + offsite replica),
    read-only (immutable) objects, retention policy and automated restore drills.
"""
import base64
import fnmatch
import hashlib
import hmac
import json
import os
import shutil
import stat
import time
import zlib
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import ransomware_guard
from common import audit, db_exec, db_query, log, raise_alert

KEYINFO = "keyinfo.json"


# ---------------------------------------------------------------- keys

def _passphrase(cfg):
    pw = os.environ.get(cfg["backup"]["passphrase_env"])
    if not pw:
        raise SystemExit(f"Set the {cfg['backup']['passphrase_env']} environment variable "
                         "(the backup encryption passphrase) before running backups.")
    return pw.encode()


def init_repository(cfg):
    repo = cfg["backup"]["repository"]
    os.makedirs(os.path.join(repo, "objects"), exist_ok=True)
    os.makedirs(os.path.join(repo, "snapshots"), exist_ok=True)
    info_path = os.path.join(repo, KEYINFO)
    if os.path.exists(info_path):
        return False
    salt = os.urandom(16)
    keys = _derive(_passphrase(cfg), salt)
    check = hmac.new(keys["mac"], b"uniguard-key-check", hashlib.sha256).hexdigest()
    with open(info_path, "w") as fh:
        json.dump({"kdf": "scrypt", "n": 2 ** 15, "r": 8, "p": 1,
                   "salt": base64.b64encode(salt).decode(), "check": check,
                   "created": datetime.now().isoformat(timespec="seconds")}, fh, indent=2)
    return True


def _derive(passphrase, salt):
    raw = Scrypt(salt=salt, length=64, n=2 ** 15, r=8, p=1).derive(passphrase)
    return {"enc": raw[:32], "mac": raw[32:]}


def load_keys(cfg):
    repo = cfg["backup"]["repository"]
    with open(os.path.join(repo, KEYINFO)) as fh:
        info = json.load(fh)
    keys = _derive(_passphrase(cfg), base64.b64decode(info["salt"]))
    check = hmac.new(keys["mac"], b"uniguard-key-check", hashlib.sha256).hexdigest()
    if not hmac.compare_digest(check, info["check"]):
        raise SystemExit("Wrong backup passphrase. Refusing to continue.")
    return keys


# ---------------------------------------------------------------- objects

def _object_path(repo, oid):
    return os.path.join(repo, "objects", oid[:2], oid)


def _seal(keys, data, aad):
    nonce = os.urandom(12)
    return nonce + AESGCM(keys["enc"]).encrypt(nonce, zlib.compress(data, 6), aad)


def _open(keys, blob, aad):
    return zlib.decompress(AESGCM(keys["enc"]).decrypt(blob[:12], blob[12:], aad))


def _write_immutable(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(blob)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)  # atomic: a power cut never leaves half an object
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


# ---------------------------------------------------------------- snapshots

def list_snapshots(cfg):
    sdir = os.path.join(cfg["backup"]["repository"], "snapshots")
    if not os.path.isdir(sdir):
        return []
    out = []
    for name in sorted(os.listdir(sdir)):
        if name.endswith(".snap"):
            out.append(name[:-5])
    return out


def _snap_path(cfg, sid):
    return os.path.join(cfg["backup"]["repository"], "snapshots", sid + ".snap")


def load_snapshot(cfg, keys, sid):
    if sid == "latest":
        snaps = list_snapshots(cfg)
        if not snaps:
            raise SystemExit("No snapshots yet.")
        sid = snaps[-1]
    with open(_snap_path(cfg, sid), "rb") as fh:
        blob = fh.read()
    manifest = json.loads(_open(keys, blob, sid.encode()))
    manifest["_digest"] = hashlib.sha256(blob).hexdigest()
    return manifest


def _excluded(cfg, path):
    ext = os.path.splitext(path)[1].lower()
    if ext in cfg["backup"].get("exclude_extensions", []):
        return True
    return any(fnmatch.fnmatch(path, pat) for pat in cfg["backup"].get("exclude_globs", []))


def _scan_sources(cfg):
    for src in cfg["backup"]["sources"]:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d != ".canary"]
            for f in files:
                full = os.path.join(root, f)
                if not _excluded(cfg, full):
                    yield src, full


def run_backup(cfg, actor="scheduler"):
    """Incremental backup. Returns a summary dict."""
    start = time.time()
    repo = cfg["backup"]["repository"]
    init_repository(cfg)
    keys = load_keys(cfg)

    # 1. Ransomware gate: never let an encrypted copy overwrite a clean history.
    guard = ransomware_guard.check_canaries(cfg)
    if guard["tripped"]:
        msg = "Canary files changed. Backup frozen to protect clean snapshots: " + ", ".join(guard["changed"])
        raise_alert(cfg, "critical", "Ransomware Guard", msg, "canary")
        _record_backup(cfg, None, "frozen", 0, 0, 0, 0, time.time() - start, msg)
        audit(cfg, actor, "backup_frozen", msg)
        return {"status": "frozen", "detail": msg}

    prev = None
    snaps = list_snapshots(cfg)
    if snaps:
        prev = load_snapshot(cfg, keys, snaps[-1])
    prev_index = {f["path"]: f for f in prev["files"]} if prev else {}

    files, suspicious = [], []
    new_objects = bytes_in = bytes_stored = 0
    for src, full in _scan_sources(cfg):
        rel = os.path.relpath(full, os.path.dirname(src))
        st = os.stat(full)
        old = prev_index.get(rel)
        if old and old["size"] == st.st_size and old["mtime"] == st.st_mtime:
            files.append(old)  # unchanged: reuse object, no read needed
            continue
        with open(full, "rb") as fh:
            data = fh.read()
        verdict = ransomware_guard.inspect_file(cfg, full, data)
        if verdict:
            suspicious.append(f"{rel} ({verdict})")
            if old:
                files.append(old)  # keep the last clean version in this snapshot
            continue
        sha = hashlib.sha256(data).hexdigest()
        oid = hmac.new(keys["mac"], data, hashlib.sha256).hexdigest()
        opath = _object_path(repo, oid)
        if not os.path.exists(opath):
            blob = _seal(keys, data, oid.encode())
            _write_immutable(opath, blob)
            new_objects += 1
            bytes_stored += len(blob)
        bytes_in += len(data)
        files.append({"path": rel, "size": st.st_size, "mtime": st.st_mtime, "sha256": sha, "oid": oid})

    limit = cfg["ransomware_guard"]["max_suspicious_files"]
    if len(suspicious) >= limit:
        msg = (f"{len(suspicious)} files look encrypted (possible ransomware). Snapshot not written. "
               f"Examples: {', '.join(suspicious[:5])}")
        raise_alert(cfg, "critical", "Ransomware Guard", msg, "entropy")
        _record_backup(cfg, None, "frozen", len(files), new_objects, bytes_in, bytes_stored,
                       time.time() - start, msg)
        audit(cfg, actor, "backup_frozen", msg)
        return {"status": "frozen", "detail": msg, "suspicious": suspicious}
    if suspicious:
        raise_alert(cfg, "warning", "Ransomware Guard",
                    f"Skipped {len(suspicious)} suspicious file(s): {', '.join(suspicious)}", "entropy-warn")

    sid = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # sortable, unique per microsecond
    manifest = {"id": sid, "created": time.time(), "host": cfg["host_name"],
                "institution": cfg["institution"], "files": files,
                "prev_id": prev["id"] if prev else None,
                "prev_digest": prev["_digest"] if prev else None}
    blob = _seal(keys, json.dumps(manifest).encode(), sid.encode())
    _write_immutable(_snap_path(cfg, sid), blob)

    replicate(cfg)
    duration = time.time() - start
    status = "ok" if not suspicious else "ok_with_warnings"
    _record_backup(cfg, sid, status, len(files), new_objects, bytes_in, bytes_stored, duration,
                   f"{len(suspicious)} suspicious skipped")
    audit(cfg, actor, "backup", f"snapshot={sid} files={len(files)} new_objects={new_objects}")
    log(cfg, f"Backup {sid}: {len(files)} files, {new_objects} new objects, "
             f"{bytes_in/1024:.1f} KiB read, {bytes_stored/1024:.1f} KiB stored, {duration:.2f}s")
    return {"status": status, "snapshot": sid, "files": len(files), "new_objects": new_objects,
            "bytes_in": bytes_in, "bytes_stored": bytes_stored, "duration_s": round(duration, 3),
            "suspicious": suspicious}


def _record_backup(cfg, sid, status, files, new_obj, b_in, b_stored, dur, detail):
    db_exec(cfg, "INSERT INTO backups(ts, snapshot_id, status, files, new_objects, bytes_in, "
                 "bytes_stored, duration_s, detail) VALUES (?,?,?,?,?,?,?,?,?)",
            (time.time(), sid, status, files, new_obj, b_in, b_stored, dur, detail))


# ---------------------------------------------------------------- replication (3-2-1)

def _in_window(window):
    start, end = window.split("-")
    now = datetime.now().strftime("%H:%M")
    return start <= now <= end if start <= end else (now >= start or now <= end)


def replicate(cfg):
    """Copy new repository files to every replica. Offsite copies respect the
    off-peak window so campus bandwidth is not choked during lectures."""
    repo = cfg["backup"]["repository"]
    copied = 0
    for rep in cfg["backup"].get("replicas", []):
        if rep.get("offsite") and not _in_window(cfg["backup"].get("offsite_window", "00:00-23:59")):
            continue
        for root, _, files in os.walk(repo):
            for f in files:
                if f.endswith(".part"):
                    continue
                src = os.path.join(root, f)
                dst = os.path.join(rep["path"], os.path.relpath(src, repo))
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    os.chmod(dst, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                    copied += 1
    return copied


# ---------------------------------------------------------------- verification

def verify_repository(cfg, actor="scheduler", deep=True):
    """Check the snapshot hash chain and (deep) decrypt every object and compare SHA-256."""
    keys = load_keys(cfg)
    repo = cfg["backup"]["repository"]
    problems = []
    digests = {}
    checked = set()
    pruned = _load_pruned(cfg)
    manifests = []
    for sid in list_snapshots(cfg):
        try:
            m = load_snapshot(cfg, keys, sid)
        except Exception as exc:
            problems.append(f"snapshot {sid} unreadable or tampered ({type(exc).__name__})")
            continue
        digests[sid] = m["_digest"]
        manifests.append(m)
    for m in manifests:
        sid, pid = m["id"], m.get("prev_id")
        if pid:
            if pid in digests:
                if m.get("prev_digest") != digests[pid]:
                    problems.append(f"hash chain broken between {pid} and {sid}")
            elif pid not in pruned:
                problems.append(f"snapshot {pid} referenced by {sid} is missing (deleted outside retention policy)")
        if not deep:
            continue
        for f in m["files"]:
            if f["oid"] in checked:
                continue
            checked.add(f["oid"])
            try:
                with open(_object_path(repo, f["oid"]), "rb") as fh:
                    data = _open(keys, fh.read(), f["oid"].encode())
                if hashlib.sha256(data).hexdigest() != f["sha256"]:
                    problems.append(f"object for {f['path']} hash mismatch")
            except FileNotFoundError:
                problems.append(f"object for {f['path']} missing")
            except Exception:
                problems.append(f"object for {f['path']} failed authentication (tampered)")
    ok = not problems
    audit(cfg, actor, "verify", "ok" if ok else "; ".join(problems[:5]))
    if not ok:
        raise_alert(cfg, "critical", "Backup Verify", "; ".join(problems[:5]), "verify")
    return {"ok": ok, "snapshots": len(list_snapshots(cfg)), "objects_checked": len(checked),
            "problems": problems}


def repair_from_replicas(cfg, actor="admin"):
    """Self-heal the main repository: replace any object that fails authentication
    with a good copy from the NAS or offsite replica (the point of 3-2-1)."""
    keys = load_keys(cfg)
    repo = cfg["backup"]["repository"]
    repaired, unrecoverable = [], []
    seen = set()
    for sid in list_snapshots(cfg):
        for f in load_snapshot(cfg, keys, sid)["files"]:
            oid = f["oid"]
            if oid in seen:
                continue
            seen.add(oid)
            main = _object_path(repo, oid)
            if _object_ok(keys, main, oid, f["sha256"]):
                continue
            for rep in cfg["backup"].get("replicas", []):
                cand = _object_path(rep["path"], oid)
                if _object_ok(keys, cand, oid, f["sha256"]):
                    if os.path.exists(main):
                        os.chmod(main, stat.S_IWRITE | stat.S_IREAD)
                    with open(cand, "rb") as fh:
                        _write_immutable(main, fh.read())
                    repaired.append(f["path"])
                    break
            else:
                unrecoverable.append(f["path"])
    audit(cfg, actor, "repair", f"repaired={len(repaired)} unrecoverable={len(unrecoverable)}")
    return {"repaired": repaired, "unrecoverable": unrecoverable}


def _object_ok(keys, path, oid, sha):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(_open(keys, fh.read(), oid.encode())).hexdigest() == sha
    except Exception:
        return False


# ---------------------------------------------------------------- restore

def restore(cfg, sid="latest", target=None, path_prefix="", actor="admin"):
    """Restore a snapshot (or a sub-folder of it) and verify every restored file."""
    start = time.time()
    keys = load_keys(cfg)
    m = load_snapshot(cfg, keys, sid)
    repo = cfg["backup"]["repository"]
    in_place = target is None
    restored = 0
    for f in m["files"]:
        if path_prefix and not f["path"].startswith(path_prefix):
            continue
        if in_place:
            # Paths are stored relative to each source's parent folder.
            parent = os.path.dirname(cfg["backup"]["sources"][0])
            dest = os.path.join(parent, f["path"])
        else:
            dest = os.path.join(target, f["path"])
        with open(_object_path(repo, f["oid"]), "rb") as fh:
            data = _open(keys, fh.read(), f["oid"].encode())
        if hashlib.sha256(data).hexdigest() != f["sha256"]:
            raise RuntimeError(f"Integrity failure on {f['path']}; aborting restore.")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".restoring"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)
        os.utime(dest, (f["mtime"], f["mtime"]))
        restored += 1
    duration = time.time() - start
    db_exec(cfg, "INSERT INTO restores(ts, snapshot_id, target, files, duration_s, verified, detail) "
                 "VALUES (?,?,?,?,?,?,?)",
            (time.time(), m["id"], target or "in-place", restored, duration, 1, path_prefix or "all"))
    audit(cfg, actor, "restore", f"snapshot={m['id']} files={restored} target={target or 'in-place'}")
    log(cfg, f"Restored {restored} files from {m['id']} in {duration:.2f}s (RTO for this dataset)")
    return {"snapshot": m["id"], "files": restored, "duration_s": round(duration, 3)}


def remove_attack_leftovers(cfg, extensions=(".locked",)):
    """Delete ransomware output files (e.g. *.locked) and ransom notes after a restore."""
    removed = 0
    for src in cfg["backup"]["sources"]:
        for root, _, files in os.walk(src):
            for f in files:
                if f.endswith(extensions) or f.upper().startswith("READ_ME_TO_DECRYPT"):
                    os.remove(os.path.join(root, f))
                    removed += 1
    return removed


# ---------------------------------------------------------------- retention

def prune(cfg, actor="scheduler"):
    """Grandfather-father-son retention, then garbage-collect unreferenced objects."""
    keys = load_keys(cfg)
    r = cfg["backup"]["retention"]
    snaps = list_snapshots(cfg)
    keep = set(snaps[-r["keep_last"]:])
    buckets = {"keep_daily": "%Y%m%d", "keep_weekly": "%Y%W", "keep_monthly": "%Y%m"}
    for rule, fmt in buckets.items():
        seen = []
        for sid in reversed(snaps):
            stamp = datetime.strptime(sid[:15], "%Y%m%d-%H%M%S").strftime(fmt)
            if stamp not in seen:
                seen.append(stamp)
                if len(seen) <= r[rule]:
                    keep.add(sid)
    removed = [s for s in snaps if s not in keep]
    repo = cfg["backup"]["repository"]
    _save_pruned(cfg, _load_pruned(cfg) | set(removed))
    for sid in removed:
        p = _snap_path(cfg, sid)
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        os.remove(p)
    # garbage collect
    live = set()
    for sid in list_snapshots(cfg):
        live.update(f["oid"] for f in load_snapshot(cfg, keys, sid)["files"])
    gc = 0
    for root, _, files in os.walk(os.path.join(repo, "objects")):
        for f in files:
            if f not in live:
                p = os.path.join(root, f)
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
                os.remove(p)
                gc += 1
    audit(cfg, actor, "prune", f"removed_snapshots={len(removed)} gc_objects={gc}")
    return {"removed_snapshots": removed, "gc_objects": gc}


def _load_pruned(cfg):
    p = os.path.join(cfg["backup"]["repository"], "pruned.json")
    if not os.path.exists(p):
        return set()
    with open(p) as fh:
        return set(json.load(fh))


def _save_pruned(cfg, ids):
    with open(os.path.join(cfg["backup"]["repository"], "pruned.json"), "w") as fh:
        json.dump(sorted(ids), fh)


def last_backup_age_minutes(cfg):
    rows = db_query(cfg, "SELECT ts FROM backups WHERE status LIKE 'ok%' ORDER BY id DESC LIMIT 1")
    return None if not rows else (time.time() - rows[0]["ts"]) / 60
