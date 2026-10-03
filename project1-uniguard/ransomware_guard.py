"""Ransomware early-detection: canary (honey) files plus integrity gating.

Two cheap signals that work on a low-budget university server:
  1. Canary files: decoy documents nobody should touch. If their hash changes,
     something is mass-modifying files.
  2. Integrity gating: a changed .csv or .txt that suddenly has near-random
     entropy, or a .docx/.pdf that lost its file signature, is treated as
     encrypted and is NOT allowed into the backup history.
"""
import hashlib
import json
import math
import os
from collections import Counter

TEXT_TYPES = {".csv", ".txt", ".json", ".sql", ".html", ".htm", ".md", ".log", ".xml", ".py", ".php"}
MAGIC = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".pptx": [b"PK\x03\x04"],
    ".zip": [b"PK\x03\x04"],
    ".doc": [b"\xd0\xcf\x11\xe0"],
    ".xls": [b"\xd0\xcf\x11\xe0"],
}
CANARY_NAMES = ["000_bursary_salary_schedule.csv", "zzz_senate_results_master.txt"]
CANARY_TEXT = ("CANARY FILE. DO NOT EDIT. This decoy is watched by UniGuard. "
               "Any change raises a critical ransomware alert.\n") * 20


def shannon_entropy(data):
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def inspect_file(cfg, path, data):
    """Return a reason string if the file looks encrypted, else None."""
    g = cfg["ransomware_guard"]
    if not g.get("enabled", True) or not data:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext in MAGIC:
        if not any(data.startswith(m) for m in MAGIC[ext]):
            return "file signature missing"
        return None
    if ext in TEXT_TYPES:
        sample = data[:4096] + data[len(data) // 2: len(data) // 2 + 4096] + data[-4096:]
        e = shannon_entropy(sample)
        if e > g["entropy_threshold"]:
            return f"entropy {e:.2f} bits/byte"
    return None


def deploy_canaries(cfg):
    d = cfg["ransomware_guard"]["canary_dir"]
    os.makedirs(d, exist_ok=True)
    hashes = {}
    for name in CANARY_NAMES:
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(CANARY_TEXT)
        hashes[name] = _sha(p)
    with open(os.path.join(d, ".hashes.json"), "w") as fh:
        json.dump(hashes, fh)
    return hashes


def check_canaries(cfg):
    d = cfg["ransomware_guard"]["canary_dir"]
    ref = os.path.join(d, ".hashes.json")
    if not cfg["ransomware_guard"].get("enabled", True) or not os.path.exists(ref):
        return {"tripped": False, "changed": []}
    with open(ref) as fh:
        hashes = json.load(fh)
    changed = []
    for name, h in hashes.items():
        p = os.path.join(d, name)
        if not os.path.exists(p) or _sha(p) != h:
            changed.append(name)
    return {"tripped": bool(changed), "changed": changed}


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
