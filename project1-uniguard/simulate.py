"""Demo helpers for the defence: seed realistic university data, run a fake
student portal, simulate an outage and a SAFE ransomware attack, and run a
full recovery drill that measures RTO and RPO.

The "attack" only touches files inside the configured sample_data folder.
"""
import argparse
import csv
import hashlib
import http.server
import json
import os
import random
import socketserver
import subprocess
import sys
import time

from common import BASE_DIR, load_config

SURNAMES = ["Adeyemi", "Okafor", "Bello", "Ibrahim", "Eze", "Ogunleye", "Musa", "Nwosu", "Abubakar",
            "Olawale", "Chukwu", "Danjuma", "Akinola", "Usman", "Obi", "Yakubu", "Adebayo", "Okonkwo",
            "Aliyu", "Ojo", "Uche", "Garba", "Afolabi", "Ezeh", "Sani", "Balogun"]
FIRST = ["Tope", "Chiamaka", "Aisha", "Emeka", "Fatima", "Tunde", "Ngozi", "Yusuf", "Bisi", "Ifeanyi",
         "Halima", "Segun", "Amaka", "Sadiq", "Kemi", "Obinna", "Zainab", "Femi", "Chidi", "Hauwa"]
DEPTS = ["Computer Science", "Mathematics", "Physics", "Microbiology", "Accounting", "Economics",
         "Mass Communication", "Civil Engineering"]
PORTAL_PORT = 8081


def seed(cfg, students=800):
    random.seed(468)
    root = cfg["backup"]["sources"][0]
    for sub in ("registry", "bursary", "results", "lms", "staff"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "registry", "students.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["matric_no", "surname", "first_name", "department", "level", "state_of_origin", "phone"])
        for i in range(students):
            w.writerow([f"U{2021 + i % 5}/CSC/{1000 + i}", random.choice(SURNAMES), random.choice(FIRST),
                        random.choice(DEPTS), random.choice([100, 200, 300, 400]),
                        random.choice(["Lagos", "Oyo", "Kano", "Enugu", "Benue", "Kaduna", "Rivers", "Ogun"]),
                        "080" + str(random.randint(10000000, 99999999))])
    with open(os.path.join(root, "bursary", "school_fees_2025_2026.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["matric_no", "rrr_reference", "amount_ngn", "status", "date"])
        for i in range(students):
            w.writerow([f"U{2021 + i % 5}/CSC/{1000 + i}", str(random.randint(10**11, 10**12 - 1)),
                        random.choice([45000, 65000, 85000, 120000]), random.choice(["PAID", "PAID", "PENDING"]),
                        f"2025-{random.randint(9, 12):02d}-{random.randint(1, 28):02d}"])
    for course in ("CMP468", "CMP402", "CMP424", "CMP442"):
        with open(os.path.join(root, "results", f"{course}_results.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["matric_no", "ca", "exam", "total", "grade"])
            for i in range(0, students, 3):
                ca, ex = random.randint(10, 40), random.randint(20, 60)
                t = ca + ex
                g = "A" if t >= 70 else "B" if t >= 60 else "C" if t >= 50 else "D" if t >= 45 else "F"
                w.writerow([f"U{2021 + i % 5}/CSC/{1000 + i}", ca, ex, t, g])
    for n in range(1, 13):
        with open(os.path.join(root, "lms", f"CMP468_lecture_{n:02d}.txt"), "w") as fh:
            fh.write(f"CMP 468 Computer Security - Lecture {n}\n" + ("Lecture notes content. " * 400))
    with open(os.path.join(root, "staff", "payroll_october.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["staff_id", "name", "grade_level", "net_pay_ngn"])
        for i in range(120):
            w.writerow([f"SP{3000 + i}", random.choice(FIRST) + " " + random.choice(SURNAMES),
                        f"CONUASS {random.randint(1, 7)}", random.randint(150000, 900000)])
    print(f"Seeded university data in {root}")


def fingerprint(cfg):
    """SHA-256 of every source file (used to prove a restore is byte-for-byte correct)."""
    out = {}
    root = cfg["backup"]["sources"][0]
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".canary"]
        for f in files:
            p = os.path.join(r, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def attack(cfg):
    """Simulated ransomware: XOR-'encrypts' files with random bytes, renames them to .locked
    and drops a ransom note. Restricted to the demo data folder."""
    root = os.path.realpath(cfg["backup"]["sources"][0])
    if not root.startswith(os.path.realpath(BASE_DIR)):
        raise SystemExit("Safety stop: attack simulation only runs inside the project folder.")
    hit = 0
    for r, _, files in os.walk(root):
        for f in files:
            if f.endswith(".locked") or f == ".hashes.json":
                continue
            p = os.path.join(r, f)
            with open(p, "rb") as fh:
                data = fh.read()
            key = os.urandom(len(data))
            with open(p + ".locked", "wb") as fh:
                fh.write(bytes(a ^ b for a, b in zip(data, key)))
            os.remove(p)
            hit += 1
    with open(os.path.join(root, "READ_ME_TO_DECRYPT.txt"), "w") as fh:
        fh.write("Your files are encrypted. Pay 2 BTC. (CMP 468 simulation, not real)\n")
    print(f"Simulated ransomware encrypted {hit} files in {root}")
    return hit


def tamper_in_place(cfg, n=5):
    """Stealthier variant: encrypts files but keeps their names (tests entropy gating)."""
    root = cfg["backup"]["sources"][0]
    victims = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".canary"]
        victims += [os.path.join(r, f) for f in files if f.endswith(".csv")]
    for p in victims[:n]:
        with open(p, "rb") as fh:
            size = len(fh.read())
        with open(p, "wb") as fh:
            fh.write(os.urandom(size))
    print(f"Encrypted {min(n, len(victims))} CSV files in place (names unchanged)")


class _Portal(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"status":"ok","service":"student-portal"}' if self.path == "/health" else \
            b"<h1>Demo University Student Portal</h1><p>Course registration is open.</p>"
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if self.path == "/health" else "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def portal(background=False):
    if background:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "portal"], cwd=BASE_DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Student portal started in background on port", PORTAL_PORT)
        return
    pidfile = os.path.join(BASE_DIR, "data", "portal.pid")
    os.makedirs(os.path.dirname(pidfile), exist_ok=True)
    with open(pidfile, "w") as fh:
        fh.write(str(os.getpid()))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORTAL_PORT), _Portal) as httpd:
        print(f"Demo student portal on http://127.0.0.1:{PORTAL_PORT}")
        httpd.serve_forever()


def outage():
    pidfile = os.path.join(BASE_DIR, "data", "portal.pid")
    if not os.path.exists(pidfile):
        print("Portal is not running.")
        return
    pid = int(open(pidfile).read())
    try:
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/PID", str(pid)])
        else:
            os.kill(pid, 9)
        print(f"Killed student portal (pid {pid}). UniGuard should alert and restart it.")
    except OSError as exc:
        print("Could not stop portal:", exc)


def drill(cfg):
    """End-to-end ransomware recovery drill. Prints measured RPO/RTO and integrity result."""
    import backup_engine
    import ransomware_guard
    report = {}
    before = fingerprint(cfg)
    t0 = time.time()
    b = backup_engine.run_backup(cfg, actor="drill")
    report["backup"] = b
    last_good = time.time()
    time.sleep(1)

    # stealth tamper first: integrity gating must refuse to back it up
    tamper_in_place(cfg, n=5)
    report["backup_after_stealth_tamper"] = backup_engine.run_backup(cfg, actor="drill")["status"]

    attack(cfg)
    t_attack = time.time()
    detect = ransomware_guard.check_canaries(cfg)
    t_detect = time.time()
    report["canary_detected"] = detect["tripped"]
    report["detection_seconds"] = round(t_detect - t_attack, 3)
    report["backup_during_attack"] = backup_engine.run_backup(cfg, actor="drill")["status"]

    t_r = time.time()
    snaps = backup_engine.list_snapshots(cfg)
    r = backup_engine.restore(cfg, snaps[-1], None, actor="drill")
    report["leftovers_removed"] = backup_engine.remove_attack_leftovers(cfg)
    ransomware_guard.deploy_canaries(cfg)
    report["restore"] = r
    report["rto_seconds"] = round(time.time() - t_r, 3)
    report["rpo_seconds"] = round(t_attack - last_good, 3)
    after = fingerprint(cfg)
    report["files_compared"] = len(before)
    report["byte_identical"] = before == after
    report["verify"] = backup_engine.verify_repository(cfg, actor="drill")["ok"]
    report["total_drill_seconds"] = round(time.time() - t0, 3)
    print(json.dumps(report, indent=2))
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(os.path.join(BASE_DIR, "data", "drill_report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["seed", "portal", "outage", "attack", "tamper", "drill"])
    p.add_argument("--background", action="store_true")
    p.add_argument("--students", type=int, default=800)
    a = p.parse_args()
    cfg = load_config()
    if a.action == "seed":
        seed(cfg, a.students)
    elif a.action == "portal":
        portal(a.background)
    elif a.action == "outage":
        outage()
    elif a.action == "attack":
        attack(cfg)
    elif a.action == "tamper":
        tamper_in_place(cfg)
    elif a.action == "drill":
        drill(cfg)


if __name__ == "__main__":
    main()
