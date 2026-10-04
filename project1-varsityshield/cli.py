"""VarsityShield command line. Run `python cli.py --help`."""
import argparse
import getpass
import json
import os
import sys
import time

import backup_engine
import monitor
import ransomware_guard
from common import CONFIG_PATH, audit, hash_password, load_config, verify_audit_chain


def cmd_init(args):
    cfg = load_config()
    os.makedirs(os.path.dirname(cfg["database"]), exist_ok=True)
    for src in cfg["backup"]["sources"]:
        os.makedirs(src, exist_ok=True)
    created = backup_engine.init_repository(cfg)
    ransomware_guard.deploy_canaries(cfg)
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    if "admin" not in raw["users"]:
        pw = os.environ.get("VSHIELD_ADMIN_PASSWORD") or "ChangeMe@468"
        raw["users"]["admin"] = {"role": "admin", "password": hash_password(pw)}
        raw["users"]["auditor"] = {"role": "viewer", "password": hash_password(pw)}
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, indent=2)
        print(f"Created users 'admin' (admin) and 'auditor' (read-only) with password: {pw}")
    audit(cfg, "cli", "init", "repository created" if created else "repository exists")
    print("Repository:", cfg["backup"]["repository"], "(new)" if created else "(existing)")
    print("Canary files deployed in", cfg["ransomware_guard"]["canary_dir"])


def cmd_add_user(args):
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    pw = getpass.getpass("Password for %s: " % args.username)
    raw["users"][args.username] = {"role": args.role, "password": hash_password(pw)}
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, indent=2)
    print("User saved.")


def cmd_backup(args):
    print(json.dumps(backup_engine.run_backup(load_config(), actor="cli"), indent=2))


def cmd_list(args):
    cfg = load_config()
    keys = backup_engine.load_keys(cfg)
    for sid in backup_engine.list_snapshots(cfg):
        m = backup_engine.load_snapshot(cfg, keys, sid)
        print(f"{sid}  files={len(m['files']):4d}  "
              f"created={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m['created']))}")


def cmd_verify(args):
    cfg = load_config()
    res = backup_engine.verify_repository(cfg, actor="cli", deep=not args.quick)
    ok, bad = verify_audit_chain(cfg)
    res["audit_chain_ok"] = ok
    if not ok:
        res["audit_chain_broken_at"] = bad
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["ok"] and ok else 1)


def cmd_restore(args):
    cfg = load_config()
    res = backup_engine.restore(cfg, args.snapshot, args.target, args.path or "", actor="cli")
    if args.target is None and args.clean:
        res["leftovers_removed"] = backup_engine.remove_attack_leftovers(cfg)
        ransomware_guard.deploy_canaries(cfg)
    print(json.dumps(res, indent=2))


def cmd_repair(args):
    print(json.dumps(backup_engine.repair_from_replicas(load_config(), actor="cli"), indent=2))


def cmd_reset_demo(args):
    """Delete demo data, backups and users so the demo can start fresh (handles read-only files)."""
    import shutil
    import stat
    base = os.path.dirname(os.path.abspath(__file__))

    def force(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for d in ("data", "sample_data", "restore_test"):
        p = os.path.join(base, d)
        if os.path.isdir(p):
            shutil.rmtree(p, onerror=force)
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw["users"] = {}
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, indent=2)
    print("Demo reset. Run SETUP.bat (or cli.py init) again.")


def cmd_prune(args):
    print(json.dumps(backup_engine.prune(load_config(), actor="cli"), indent=2))


def cmd_monitor(args):
    cfg = load_config()
    while True:
        print(json.dumps(monitor.run_once(cfg), indent=2))
        if args.once:
            break
        time.sleep(cfg["monitor"]["interval_seconds"])


def main():
    p = argparse.ArgumentParser(description="VarsityShield: monitoring, backup and recovery for university ICT")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create repository, canaries and default users").set_defaults(fn=cmd_init)
    u = sub.add_parser("add-user", help="add or reset a dashboard user")
    u.add_argument("username")
    u.add_argument("--role", choices=["admin", "viewer"], default="viewer")
    u.set_defaults(fn=cmd_add_user)
    sub.add_parser("backup", help="run an incremental encrypted backup now").set_defaults(fn=cmd_backup)
    sub.add_parser("list", help="list snapshots").set_defaults(fn=cmd_list)
    v = sub.add_parser("verify", help="verify snapshots, objects and audit chain")
    v.add_argument("--quick", action="store_true", help="check hash chain only")
    v.set_defaults(fn=cmd_verify)
    r = sub.add_parser("restore", help="restore a snapshot")
    r.add_argument("--snapshot", default="latest")
    r.add_argument("--target", help="restore into this folder (default: in place)")
    r.add_argument("--path", help="only restore paths starting with this prefix")
    r.add_argument("--clean", action="store_true", help="after in-place restore, delete *.locked files")
    r.set_defaults(fn=cmd_restore)
    sub.add_parser("repair", help="replace tampered objects using replica copies").set_defaults(fn=cmd_repair)
    sub.add_parser("reset-demo", help="delete demo data, backups and users").set_defaults(fn=cmd_reset_demo)
    sub.add_parser("prune", help="apply retention policy").set_defaults(fn=cmd_prune)
    m = sub.add_parser("monitor", help="run monitoring checks")
    m.add_argument("--once", action="store_true")
    m.set_defaults(fn=cmd_monitor)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
