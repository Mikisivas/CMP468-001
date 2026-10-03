# VarsityShield: Automated Monitoring, Backup and Recovery for University Digital Infrastructure

CMP 468 (Computer Security) project 1. VarsityShield watches your servers and services, takes encrypted
3-2-1 backups, blocks ransomware-encrypted files from entering the backup history, and restores data
with a measured RTO.

Default login after setup: `admin` / `ChangeMe@468` (change it before your demo).

---

## Part A. Step-by-step setup on your own laptop

You need about 20 minutes. Commands are given for Windows (PowerShell) and Linux/macOS.

### Step 1. Install Python

1. Download Python 3.10 or newer from https://www.python.org/downloads/
2. Windows: tick **"Add python.exe to PATH"** on the first installer screen.
3. Check it works:
   ```
   python --version
   ```
   (On Linux/macOS use `python3` everywhere below.)

### Step 2. Get the project folder

Copy the `project1-varsityshield` folder to your laptop, for example `C:\CMP468\project1-varsityshield`, then open
a terminal inside it:
```
cd C:\CMP468\project1-varsityshield
```

### Step 3. Create a virtual environment and install packages

Windows:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Linux/macOS:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
You should now see `(venv)` at the start of your prompt.

### Step 4. Set the backup passphrase

The passphrase derives the AES-256 key. It is never written to disk. If you lose it, the backups cannot
be decrypted, so write it down.

Windows:
```
$env:VSHIELD_PASSPHRASE="Choose-A-Long-Passphrase-2026"
$env:VSHIELD_SECRET_KEY="any-long-random-text-for-web-sessions"
```
Linux/macOS:
```
export VSHIELD_PASSPHRASE='Choose-A-Long-Passphrase-2026'
export VSHIELD_SECRET_KEY='any-long-random-text-for-web-sessions'
```
You must set these again every time you open a new terminal.

### Step 5. Initialise VarsityShield

```
python cli.py init
```
This creates the encrypted repository in `data/repository`, deploys two canary (decoy) files, and creates
two users: `admin` (full rights) and `auditor` (read-only). To pick your own password, set
`VSHIELD_ADMIN_PASSWORD` before running `init`.

### Step 6. Create demo university data

```
python simulate.py seed
```
This writes student records, school fees, results, lecture notes and payroll into `sample_data/`.

### Step 7. Start the demo student portal (the service VarsityShield will monitor)

```
python simulate.py portal --background
```

### Step 8. Take the first backup and verify it

```
python cli.py backup
python cli.py verify
python cli.py list
```

### Step 9. Open the dashboard

```
python app.py
```
Open http://127.0.0.1:5000 in your browser and log in as `admin`. Leave this terminal running. The
scheduler inside `app.py` now monitors every 15 seconds and backs up every 30 minutes.

Open a **second terminal** for Part B (repeat Step 3 activation and Step 4 variables in it).

---

## Part B. Live demonstration script for the defence (about 6 minutes)

Run these in the second terminal while the dashboard is on the projector.

| # | Say this | Run this | What the panel sees |
|---|----------|----------|---------------------|
| 1 | "This is our university's live status." | (show dashboard) | CPU, memory, disk, services UP, canaries Intact |
| 2 | "The student portal crashes." | `python simulate.py outage` | Within 15 s: critical alert, then VarsityShield restarts it and it shows UP |
| 3 | "Ransomware encrypts results quietly, without renaming files." | `python simulate.py tamper` then click **Run backup now** | Backup status `frozen`, entropy alert. Encrypted files never enter the history |
| 4 | "Now a full ransomware attack." | `python simulate.py attack` | Canaries TRIPPED, critical alert. Open `sample_data` to show `.locked` files and the ransom note |
| 5 | "We recover." | Backups & Restore page, click **Restore** on the newest snapshot | Files back, measured RTO shown on dashboard |
| 6 | "Prove the backup can't be secretly altered." | Click **Verify integrity** | Passes. Then show the Audit log page: hash chain INTACT |
| 7 | "Everything at once, with numbers." | `python simulate.py drill` | Prints RTO, RPO, `byte_identical: true` |

Step 5 by command line instead of the browser:
```
python cli.py restore --snapshot latest --clean
```

Optional tamper demonstration (Linux/macOS):
```
obj=$(find data/repository/objects -type f | head -1); chmod u+w "$obj"; printf 'Z' | dd of="$obj" bs=1 seek=20 conv=notrunc
python cli.py verify      # fails: tampered
python cli.py repair      # fixes it from the NAS replica
python cli.py verify      # passes
```

To reset everything before the real defence: stop `app.py`, delete the `data` and `sample_data` folders,
remove the `"admin"` and `"auditor"` entries from `"users"` in `config.json`, and repeat Steps 5 to 9.

---

## Part C. Deploying on a real university server

1. **Choose what to protect.** Edit `config.json` → `backup.sources`, for example
   `["/var/www/portal/uploads", "/backups/db_dumps"]` or `["D:\\Registry", "D:\\Results"]`.
2. **Dump databases first.** Add a scheduled job 5 minutes before each backup:
   - MySQL: `mysqldump --single-transaction portal > /backups/db_dumps/portal.sql`
   - PostgreSQL: `pg_dump -Fp results > /backups/db_dumps/results.sql`
3. **Set replicas (3-2-1).** In `backup.replicas`, point the first path at a second disk or NAS share and the
   second at an offsite location (another campus share, or an S3 bucket with Object Lock mounted with
   rclone). Rotate one USB disk weekly and keep it unplugged in another building.
4. **Set the off-peak window** (`offsite_window`, e.g. `"00:00-05:00"`) so uploads don't slow lectures.
5. **Add real services** in `monitor.services` (portal URL, LMS URL, database port, mail server port) and a
   `restart_command` for each, for example `systemctl restart apache2`.
6. **Enable alerts** in `alerts.channels`:
   - Email: fill SMTP details and set `VSHIELD_SMTP_PASSWORD`.
   - Telegram: create a bot with @BotFather, put the chat id in config, set `VSHIELD_TELEGRAM_TOKEN`.
   - SMS: use a Nigerian gateway (Termii or Africa's Talking) and set `VSHIELD_SMS_KEY`.
   Then set `"enabled": true`.
7. **Run as a service.**
   - Linux (systemd), file `/etc/systemd/system/varsityshield.service`:
     ```
     [Unit]
     Description=VarsityShield
     After=network.target
     [Service]
     WorkingDirectory=/opt/varsityshield
     EnvironmentFile=/etc/varsityshield.env
     ExecStart=/opt/varsityshield/venv/bin/python app.py
     Restart=always
     [Install]
     WantedBy=multi-user.target
     ```
     Put the passphrase in `/etc/varsityshield.env` with `chmod 600`. Then `systemctl enable --now varsityshield`.
   - Without the dashboard, use cron: `*/30 * * * * cd /opt/varsityshield && venv/bin/python cli.py backup`
   - Windows: Task Scheduler → Create Task → Trigger every 30 minutes → Action
     `C:\CMP468\project1-varsityshield\venv\Scripts\python.exe cli.py backup`, "Start in" the project folder.
8. **Protect the dashboard.** Keep `host` as `127.0.0.1` and reach it through SSH or put it behind Nginx
   with HTTPS on the staff VLAN only.
9. **Drill every quarter** with `python cli.py restore --snapshot latest --target D:\restore_test` and record
   the time.

---

## Command reference

| Command | Purpose |
|---------|---------|
| `python cli.py init` | Create repository, canaries and default users |
| `python cli.py add-user NAME --role admin` | Add or reset a dashboard user |
| `python cli.py backup` | Incremental encrypted backup now |
| `python cli.py list` | List snapshots |
| `python cli.py verify [--quick]` | Check hash chain, decrypt and hash every object, check audit chain |
| `python cli.py repair` | Replace damaged objects with good replica copies |
| `python cli.py restore [--snapshot ID] [--target DIR] [--path PREFIX] [--clean]` | Restore |
| `python cli.py prune` | Apply retention policy |
| `python cli.py monitor [--once]` | Run monitoring checks |
| `python simulate.py seed / portal / outage / tamper / attack / drill` | Demo helpers |

## Troubleshooting

- **"Set the VSHIELD_PASSPHRASE environment variable"**: you opened a new terminal. Repeat Step 4.
- **"Wrong backup passphrase"**: the passphrase differs from the one used at `init`.
- **Port 5000 in use**: change `dashboard.port` in `config.json`.
- **Portal shows DOWN on Windows after outage**: wait one monitoring cycle (15 s). The restart command
  runs `python simulate.py portal --background`.
- **`pip` not found**: reinstall Python with "Add to PATH" ticked, or use `python -m pip`.
