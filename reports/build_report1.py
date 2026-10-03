"""Builds Report 1: UniGuard (automated monitoring, backup and recovery)."""
import os

from docx_helpers import Report

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Report1_UniGuard_Monitoring_Backup_Recovery.docx")

r = Report()
r.title_page("UniGuard: An Automated Monitoring, Backup and Recovery System for University Digital Infrastructure",
             "A ransomware-resilient design for Nigerian universities")

# ------------------------------------------------------------ front matter
r.h1("DECLARATION")
r.p("I declare that this project report and the accompanying software were written by me as part of the "
    "requirements of CMP 468 (Computer Security). Every source used has been cited. All literature cited in "
    "this report was published between 2021 and 2026.")
r.p("Signature: ____________________          Date: ____________________")
r.page_break()

r.h1("ABSTRACT")
r.p("Nigerian universities now run admissions, course registration, school fees, examination results, payroll "
    "and e-learning on digital platforms. Most of them still protect these systems with antivirus and firewalls "
    "alone. Studies of Nigerian higher education institutions report weak incident response, few monitoring "
    "platforms, poor funding, unstable electricity and a shortage of skilled staff (Olugbile et al., 2025; "
    "Yunisa, 2025; Aba, 2026). When a server fails or ransomware strikes, a university without tested backups "
    "may lose a whole session of results. This project designed, built and tested UniGuard, a low-cost system "
    "that combines four functions: (1) continuous monitoring of servers and services with threshold and "
    "statistical anomaly alerts, (2) encrypted, de-duplicated, incremental backups with a 3-2-1 replica "
    "layout, (3) ransomware early detection with canary files and entropy-based integrity gating, and "
    "(4) verified, measurable recovery. Backups are sealed with AES-256-GCM, keys are derived with scrypt, "
    "snapshots form a SHA-256 hash chain, and every administrative action enters a tamper-evident audit log. "
    "In tests on a 9.0 MiB sample of university records, the first backup took 0.50 s and stored 2.04 MiB "
    "(a 77.3% reduction). Unchanged incremental runs took 0.09 s. A simulated ransomware attack was detected "
    "by canary files, the backup history was frozen before encrypted files could enter it, and all 19 files "
    "were restored byte-for-byte in 0.15 s. A tampered backup object was detected and repaired from a replica. "
    "UniGuard runs on one ordinary server with Python, so a Nigerian university ICT unit can adopt it without "
    "licence fees.")
r.p("**Keywords:** backup and recovery, ransomware, monitoring, AES-256-GCM, integrity, RPO, RTO, "
    "Nigerian universities, NDPA 2023.")
r.page_break()

r.h1("TABLE OF CONTENTS")
r.toc()
r.page_break()

# ------------------------------------------------------------ chapter 1
r.h1("CHAPTER ONE: INTRODUCTION")
r.h2("1.1 Background of the Study")
r.p("A Nigerian university is now a digital organisation. Students pay fees through Remita, register courses "
    "on a portal, read lecture notes on a learning management system and check results online. The bursary "
    "runs payroll from a database, and the registry holds admission and graduation records that must last for "
    "decades. Each of these systems is a target. A survey of 387 stakeholders in Delta State institutions found "
    "wide use of firewalls and antivirus software but sparse deployment of intrusion detection and security "
    "monitoring platforms. Incident response mechanisms were inconsistent. In South-South university "
    "libraries, 54.0% of respondents reported exposure to ransomware and 57.1% to data breaches (Aba, 2026).")
r.p("Ransomware changed what backup means. Older backup plans assumed that disks fail by accident. A modern "
    "attacker encrypts production data, then looks for the backups and encrypts or deletes those too. "
    "Recovery-focused research now treats backup integrity and fast, verified restoration as security goals in "
    "their own right (Varshney et al., 2026; Tajudeen et al., 2026). The 3-2-1-1-0 rule (three copies, two "
    "media, one offsite, one offline or immutable, zero errors on verification) captures this shift "
    "(Lysetskyi et al., 2025).")
r.p("Nigeria adds local pressures. Power supply is erratic, so servers run on inverters and generators. "
    "Internet bandwidth is expensive, which makes nightly multi-gigabyte cloud uploads hard. Funding is thin, "
    "so commercial backup suites with per-terabyte licences are out of reach for many state universities. "
    "The Nigeria Data Protection Act (NDPA) 2023 also makes the university a data controller that must keep "
    "personal data confidential, accurate and available (Edet et al., 2026).")

r.h2("1.2 Statement of the Problem")
r.p("Four gaps motivate this work:")
r.bullets([
    "**No continuous visibility.** Many ICT units learn of an outage when students complain on WhatsApp. "
    "Monitoring platforms are rarely deployed (Olugbile et al., 2025).",
    "**Backups that are never tested.** Copies are made to an external drive when someone remembers, are not "
    "encrypted, and are never restored in a drill, so nobody knows the real recovery time.",
    "**Backups exposed to ransomware.** Backups sit on a mapped network share that the same malware can "
    "reach. Nothing stops an encrypted file from replacing the last clean copy.",
    "**No evidence trail.** When records change, there is no tamper-evident log of who restored, deleted or "
    "modified what, which weakens forensic readiness (Leonard et al., 2026).",
])

r.h2("1.3 Aim and Objectives")
r.p("The aim is to design, implement and evaluate an automated monitoring, backup and recovery system for "
    "university digital infrastructure that remains trustworthy under ransomware attack. The objectives are to:")
r.bullets([
    "monitor host health (CPU, memory, disk, network, battery power) and service availability, and raise "
    "alerts through email, Telegram or SMS.",
    "detect unusual behaviour with an adaptive z-score method in addition to static thresholds.",
    "take scheduled, incremental, encrypted and de-duplicated backups with replicas on a second disk and an "
    "offsite location.",
    "detect ransomware activity early and stop encrypted data from entering the backup history.",
    "verify backups automatically and restore them with measured Recovery Time Objective (RTO) and Recovery "
    "Point Objective (RPO).",
    "protect the system itself with authentication, role-based access, CSRF protection and a hash-chained "
    "audit log.",
    "evaluate the system with a reproducible attack and recovery drill.",
], numbered=True)

r.h2("1.4 Scope and Limitations")
r.p("UniGuard protects file-level data and monitors one or more servers from a central node. It was tested "
    "with synthetic but realistic university records (student register, fees, results, lecture notes and "
    "payroll). It does not replace endpoint antivirus or a network firewall. Database engines such as MySQL "
    "or PostgreSQL are protected by backing up their dump files, which a pre-backup hook can create. The test "
    "dataset is small (9.0 MiB), so the timing figures show relative behaviour rather than production "
    "throughput.")

r.h2("1.5 Significance of the Study")
r.p("The work gives a Nigerian ICT unit a free, auditable tool it can run on existing hardware. It turns "
    "abstract CMP 468 topics into working controls: encryption and decryption protect backup confidentiality, "
    "hashing protects integrity, replication protects availability, and the audit log supports security "
    "policy enforcement. It also produces evidence (RTO, RPO, verification reports) that management can use "
    "when it reports to the university council or to the Nigeria Data Protection Commission.")

r.h2("1.6 Relation to the CMP 468 Course Outline")
r.table("Mapping of course topics to UniGuard features",
        ["CMP 468 topic", "Where it appears in UniGuard"],
        [["Overview of security in computing", "CIA triad drives the design: AES-GCM (confidentiality), "
          "SHA-256/HMAC chain (integrity), 3-2-1 replicas and restore drills (availability)"],
         ["Characteristics of computer intrusion", "Ransomware behaviour model: mass modification, renamed "
          "extensions, high-entropy output, ransom note"],
         ["Types of security breaches", "Data destruction, data tampering, unauthorised access to the "
          "dashboard, insider deletion of backups"],
         ["Security vulnerability", "Unencrypted, untested, network-reachable backups. Weak passwords. "
          "Missing audit trail"],
         ["Classes of attacks", "Ransomware, brute-force login, CSRF, backup tampering, replay of deleted "
          "snapshots"],
         ["Methods of defence and controls", "Preventive (encryption, RBAC, lockout), detective (monitoring, "
          "canaries, entropy, verification), corrective (restore, repair, self-healing restart)"],
         ["Data security: encryption and decryption", "AES-256-GCM per object, scrypt key derivation, "
          "HMAC-SHA256 object identifiers"],
         ["Database security", "Backup of DB dumps, SQLite audit store, parameterised SQL queries"],
         ["Network security", "Service reachability checks, offsite replication window, security headers, "
          "SameSite cookies"],
         ["Security policies and standards", "Backup policy (RPO 60 min), retention policy, NIST CSF 2.0 "
          "Recover function, ISO/IEC 27001:2022 controls, NDPA 2023"]],
        widths=[5, 11])

r.h2("1.7 Definition of Terms")
r.bullets([
    "**RPO (Recovery Point Objective):** the maximum amount of data, measured in time, that the university "
    "accepts to lose. An RPO of 60 minutes means at most one hour of work is lost.",
    "**RTO (Recovery Time Objective):** the maximum time allowed to restore a service after an incident.",
    "**Snapshot:** a consistent, point-in-time record of all protected files.",
    "**Canary file:** a decoy file that no legitimate user edits. Any change signals malicious activity.",
    "**Shannon entropy:** a measure (0 to 8 bits per byte) of randomness. Encrypted data is close to 8.",
    "**Immutable backup:** a copy that cannot be changed after it is written.",
])
r.page_break()

# ------------------------------------------------------------ chapter 2
r.h1("CHAPTER TWO: LITERATURE REVIEW")
r.p("This review covers only studies published from 2021 to 2026. It is arranged in four themes: the "
    "cybersecurity situation of Nigerian universities, infrastructure monitoring, backup and disaster "
    "recovery, and ransomware-resilient recovery.")

r.h2("2.1 Conceptual Framework")
r.p("The study rests on the Confidentiality, Integrity and Availability (CIA) triad, which Edet et al. (2026) "
    "also used to frame cybersecurity in Nigerian academic libraries. Availability is the property most "
    "directly threatened by ransomware and hardware failure, but a backup that is readable by an attacker "
    "fails confidentiality, and a backup that can be silently altered fails integrity. Recovery is therefore "
    "treated as a security function, which matches the Recover function of the NIST Cybersecurity Framework "
    "2.0 (2024). The second concept is the recovery objective pair RPO and RTO. Tatineni (2023) identifies "
    "them as the core parameters of any disaster recovery plan, and they are the main evaluation metrics of "
    "this project.")

r.h2("2.2 Cybersecurity in Nigerian Universities")
r.p("Olugbile et al. (2025) used Design Science Research to build a Cybersecurity Readiness Index for Nigerian "
    "universities. Of twenty universities sampled, 65% fell in the lowest readiness tier, with the largest gaps "
    "in event management and post-event capability, which is exactly where backup and recovery sit. Yunisa "
    "(2025) lists poor funding, weak infrastructure, shortage of professionals and decentralised networks as "
    "the main obstacles. Farouk et al. (2024) propose a risk management framework that includes intrusion "
    "detection and threat analytics, and Adamu (2025) compares AES, RSA and hybrid encryption for protecting "
    "sensitive records in polytechnics, concluding that hybrid schemes are stronger but more costly. Onche "
    "et al. (2023) show that staff use of personal devices in administrative offices, combined with "
    "intermittent power and ageing networks, raises the chance of ransomware contamination of institutional "
    "records. Leonard et al. (2026) find that digital forensic readiness in Nigerian public universities is "
    "underdeveloped, and recommend integrated frameworks. Student behaviour adds risk: Yusuf et al. (2026) "
    "found that many University of Ilesa students regularly use insecure free Wi-Fi.")
r.p("Across these studies the pattern is consistent. Prevention tools exist, but monitoring, incident "
    "response and recovery are weak. None of the reviewed Nigerian studies built and measured a working "
    "recovery system, which is the gap this project addresses.")

r.h2("2.3 Infrastructure Monitoring and Alerting")
r.p("Open-source monitoring stacks dominate recent work. Pragathi et al. (2024) deployed Prometheus, Grafana "
    "and Node Exporter in Kubernetes for real-time CPU, memory and disk visibility. Sai (2024) added Loki for "
    "logs and Alerta for threshold alerts. Simili et al. (2021) described a Prometheus, Loki and Grafana system "
    "at the Glasgow Tier-2 cluster that both alerts and performs simple automated recovery actions, and argued "
    "that funding-constrained academic institutions benefit most because automation frees scarce staff. "
    "Bajpai (2022) automated ticket creation from alerts. Static thresholds produce false alarms. Zhang et al. "
    "(2026) used a sliding-window mean and standard deviation to adjust thresholds dynamically and reported "
    "fewer false positives. Rafiq et al. (2025) used regression, K-means and LSTM models at the edge and reported "
    "a 95% reduction in downtime across 500 nodes, and Kasinadhuni (2026) combined four anomaly detectors with "
    "log correlation to cut time to first insight from about 90 minutes to under 5.")
r.p("UniGuard adopts the lighter ideas from this body of work: sliding-window z-score anomaly detection "
    "(Zhang et al., 2026), alert de-duplication, and self-healing restarts (Simili et al., 2021). It avoids "
    "running a full Prometheus and Kubernetes stack, which would be heavy for a single university server, but "
    "its SQLite metric store could be exported to Prometheus later.")

r.h2("2.4 Backup and Disaster Recovery in Education")
r.p("Muthoni et al. (2021) studied 92 university staff in Kenya and found that African institutions are slow "
    "to adopt cloud business continuity because of cost and skills. Their Infrastructure as Code experiment "
    "with Ansible and Terraform cut human error during recovery. Vinisha et al. (2025) designed a hybrid "
    "architecture for Tier-2 and Tier-3 colleges where an on-demand cloud server takes over when the single "
    "on-premises web server fails. Dotasara et al. (2022) proposed compressing and encrypting education data "
    "before cloud storage. Plaka (2022) mapped 45 studies and named data security, integrity and failure "
    "prediction as the open problems of backup. Ganesan (2024) and Tatineni (2023) review cloud disaster "
    "recovery practice, and Tarasenko et al. (2025) show that reliable infrastructure and cybersecurity "
    "standards are among the main challenges of the cloud university model. Lysetskyi et al. (2025) recommend "
    "the 3-2-1-1-0 rule with air-gapped, immutable copies as the most effective strategy against ransomware.")

r.h2("2.5 Ransomware-Resilient Backup and Recovery")
r.p("Recent work moves from detection alone towards guaranteed recovery. Baek et al. (2021) built detection "
    "and recovery into SSD firmware and reported instant recovery with no data loss, but the approach needs "
    "special hardware. Kodali et al. (2026) proposed an offline backup tool that uses SHA-256 change detection, "
    "ZIP compression and AES-256-GCM, reporting a 20 to 23% storage reduction and successful tamper detection. "
    "Amoruso et al. (2026) introduced integrity-gated backup: a changed file is backed up only if its header "
    "signature and spot entropy look normal, which preserved 100% of files against full-file encryption. "
    "Varshney et al. (2026) combined behavioural detection with an isolated, immutable vault and an automated "
    "orchestrator that cut mean recovery time from hours to under twelve minutes. Omopariola et al. (2026) "
    "paired machine learning detection with isolated backups and user education. Kumar et al. (2026) verified "
    "backup integrity with Merkle trees before restoration. Ilau et al. (2025) simulated 9,000 recovery configurations and showed that recovery "
    "choices strongly change organisational resilience. Tajudeen et al. (2026) report that structured recovery "
    "achieved up to 70% faster restoration in their framework evaluation.")

r.h2("2.6 Summary of Reviewed Works and Research Gap")
r.table("Summary of closely related works (2021 to 2026)",
        ["Author (Year)", "Approach", "Strength", "Limitation for a Nigerian university"],
        [["Simili et al. (2021)", "Prometheus/Loki monitoring with automated recovery actions",
          "Reduces staff workload", "No backup or ransomware handling"],
         ["Muthoni et al. (2021)", "Infrastructure as Code cloud failover", "Fast, repeatable recovery",
          "Depends on steady cloud bandwidth and budget"],
         ["Baek et al. (2021)", "SSD firmware detection and recovery", "Zero data loss",
          "Needs special SSD hardware"],
         ["Lysetskyi et al. (2025)", "3-2-1-1-0 rule with air gap", "Clear policy guidance",
          "Policy only, no implementation"],
         ["Vinisha et al. (2025)", "Hybrid cloud web failover", "Low cost for small colleges",
          "Covers web server only, no data integrity checks"],
         ["Amoruso et al. (2026)", "Integrity-gated file backup", "Stops encrypted files entering backups",
          "Windows endpoint only, no monitoring"],
         ["Kodali et al. (2026)", "SHA-256 change detection with AES-256-GCM", "Lightweight and offline",
          "Single user, no replicas or audit log"],
         ["Varshney et al. (2026)", "Immutable vault and recovery orchestrator", "Recovery under 12 minutes",
          "Enterprise-scale design"],
         ["Olugbile et al. (2025)", "Readiness index for Nigerian universities",
          "Local evidence of gaps", "Assessment only, no tool"]],
        widths=[3.2, 4.3, 3.8, 4.7])
r.p("**Gap.** No reviewed study combines monitoring, encrypted 3-2-1 backup, ransomware gating, automated "
    "verification, measured recovery and a tamper-evident audit trail in one low-cost tool designed for the "
    "power, bandwidth and budget conditions of Nigerian universities. UniGuard fills that gap.")
r.page_break()

# ------------------------------------------------------------ chapter 3
r.h1("CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN")
r.h2("3.1 Research Methodology")
r.p("The project follows Design Science Research, the same method Olugbile et al. (2025) used for Nigerian "
    "university readiness. The steps were: identify the problem from literature, define objectives, design "
    "and build the artefact, demonstrate it with a simulated university dataset, evaluate it with measurable "
    "metrics, and communicate the results in this report. Development used an incremental prototyping model, "
    "with each component tested before integration.")

r.h2("3.2 Analysis of the Existing System")
r.p("In a typical Nigerian university ICT centre, a system administrator copies database dumps to an "
    "external hard disk weekly or monthly. The disk stays connected to the server or sits in the same room. "
    "Monitoring is manual. There is no written RPO or RTO, and restores are attempted only during an incident. "
    "The weaknesses are: a single copy in a single location, no encryption, no integrity checks, exposure to "
    "the same ransomware that hits the server, and no record of who did what.")

r.h2("3.3 Requirements of the Proposed System")
r.table("Functional and non-functional requirements",
        ["ID", "Requirement", "Type"],
        [["F1", "Collect CPU, memory, disk, network and battery metrics every 15 seconds", "Functional"],
         ["F2", "Check HTTP and TCP services and restart a failed service automatically", "Functional"],
         ["F3", "Raise de-duplicated alerts by email, Telegram or SMS gateway", "Functional"],
         ["F4", "Run incremental encrypted backups every 30 minutes (RPO 60 minutes)", "Functional"],
         ["F5", "Replicate to a second disk and to an offsite location in an off-peak window", "Functional"],
         ["F6", "Detect ransomware with canary files and entropy or signature checks", "Functional"],
         ["F7", "Verify all snapshots and objects and repair from replicas", "Functional"],
         ["F8", "Restore all data, a folder, or into a separate folder for inspection", "Functional"],
         ["N1", "Backups unreadable without the passphrase (AES-256-GCM)", "Security"],
         ["N2", "Any change to a stored backup must be detected", "Security"],
         ["N3", "Only administrators may restore. Viewers have read-only access", "Security"],
         ["N4", "Run on one ordinary server with free software", "Cost"],
         ["N5", "Dashboard works on the campus LAN without internet access", "Usability"]],
        widths=[1.2, 12, 2.8])

r.h2("3.4 System Architecture")
r.p("UniGuard has five modules that share a SQLite database. The diagram after this list shows how "
    "data moves between them:")
r.bullets([
    "**Monitor** (monitor.py) gathers host metrics with psutil, probes services, applies static thresholds and "
    "a sliding-window z-score test, checks backup age against the RPO, checks the canaries, and issues "
    "restart commands for failed services.",
    "**Backup engine** (backup_engine.py) scans source folders, skips unchanged files using size and "
    "modification time, encrypts new content, writes immutable objects, writes an encrypted snapshot "
    "manifest linked to the previous one, and replicates to every replica path.",
    "**Ransomware guard** (ransomware_guard.py) deploys and checks canary files and inspects each changed file "
    "before it can enter a snapshot.",
    "**Alerting and audit** (common.py) stores alerts, sends them through enabled channels, and appends every "
    "action to a hash-chained audit log.",
    "**Dashboard and scheduler** (app.py) runs the periodic jobs and serves a Flask web interface protected by "
    "login, roles and CSRF tokens. A command line tool (cli.py) offers the same operations for cron or "
    "Windows Task Scheduler.",
])
r.code("  [Servers / services] --metrics, health--> [Monitor] --alerts--> [Email | Telegram | SMS]\n"
       "         |                                     |\n"
       "   [Source data] --> [Ransomware guard] --> [Backup engine: compress -> AES-256-GCM -> HMAC id]\n"
       "                                               |              |                 |\n"
       "                                     [Repository]   [NAS replica]   [Offsite replica]\n"
       "                                               |\n"
       "             [Verify + Repair] <---------------+---------------> [Restore + RTO log]\n"
       "                                               |\n"
       "                    [SQLite: metrics, alerts, backups, restores, audit chain] <-- [Dashboard]")

r.h2("3.5 Security Design")
r.h3("3.5.1 Key management")
r.p("The administrator supplies a passphrase through an environment variable. It is never written to disk. "
    "scrypt (N = 2^15, r = 8, p = 1) with a random 16-byte salt derives 64 bytes: 32 for encryption and 32 for "
    "message authentication. A key-check value lets the system refuse a wrong passphrase before it touches any "
    "data. Losing the passphrase means losing the backups, so the policy in Section 5.3 requires a sealed copy "
    "in the Vice-Chancellor's safe or the bursary vault.")
r.h3("3.5.2 Object encryption and identification")
r.p("Each file's content is compressed with zlib and encrypted with AES-256 in Galois/Counter Mode using a "
    "fresh 96-bit nonce. The object identifier is HMAC-SHA256(key, plaintext). Two identical files share one "
    "object (de-duplication), but an attacker who sees the repository cannot test whether a known document is "
    "present, which would be possible with a plain SHA-256 name. The identifier is also bound to the "
    "ciphertext as associated data, so an object swapped into another name fails authentication.")
r.h3("3.5.3 Tamper-evident snapshots and audit log")
r.p("Each encrypted snapshot manifest stores the SHA-256 digest of the previous manifest. Deleting or editing "
    "an old snapshot breaks the chain, unless the retention policy recorded the deletion. The audit log uses "
    "the same chaining, so an insider who deletes a row is detected on the audit page.")
r.h3("3.5.4 Immutability and replication")
r.p("Objects are written to a temporary file, flushed, atomically renamed and set read-only, so a power cut "
    "never leaves half an object. Replicas apply the 3-2-1 rule. The offsite replica runs inside a configurable "
    "off-peak window to save daytime campus bandwidth. In production the offsite path should point at a "
    "different campus, an S3-compatible bucket with object lock, or a removable disk rotated weekly, so that "
    "at least one copy is offline (Lysetskyi et al., 2025).")
r.h3("3.5.5 Ransomware early detection")
r.p("Two decoy files are placed in the protected folder. Ransomware encrypts files in bulk, so it usually hits "
    "the canaries. When their hashes change, UniGuard raises a critical alert and freezes backups. "
    "Independently, every changed file is inspected: text formats (CSV, TXT, SQL, JSON) with Shannon entropy "
    "above 7.2 bits per byte, or Office, PDF and image files whose signature bytes are missing, are treated "
    "as encrypted. If three or more such files appear, the snapshot is not written, following the "
    "integrity-gating idea of Amoruso et al. (2026). The last clean version stays in the history.")
r.h3("3.5.6 Dashboard protection")
r.p("Passwords are stored as PBKDF2-SHA256 hashes with 310,000 iterations. Five failed logins from one address "
    "lock it for five minutes. Sessions use HttpOnly and SameSite=Strict cookies, and every state-changing "
    "request carries a CSRF token. Two roles exist: admin (backup, verify, restore, prune) and viewer "
    "(read-only, for auditors). Responses carry X-Frame-Options, X-Content-Type-Options and Referrer-Policy "
    "headers.")

r.h2("3.6 Algorithms")
r.h3("3.6.1 Incremental backup")
r.code("for each file in sources (excluding canaries and *.locked):\n"
       "    if size and mtime equal previous snapshot: reuse previous entry; continue\n"
       "    data <- read(file)\n"
       "    if inspect(file, data) says 'encrypted': add to suspicious; keep previous clean entry; continue\n"
       "    oid <- HMAC_SHA256(k_mac, data)\n"
       "    if object oid not stored: store nonce || AES_GCM(k_enc, zlib(data), aad=oid) read-only\n"
       "if canary changed or |suspicious| >= 3: alert CRITICAL; record 'frozen'; stop\n"
       "manifest <- {files, prev_id, SHA256(prev_manifest)}; store AES_GCM(manifest); replicate")
r.h3("3.6.2 Adaptive anomaly detection")
r.p("For CPU and memory, the last 30 readings form a window with mean μ and standard deviation σ. A new "
    "reading x is anomalous when |x − μ| / σ ≥ 3. Windows with σ below 1 percentage point are ignored "
    "to avoid alerts on flat series.")
r.h3("3.6.3 Grandfather-father-son retention")
r.p("The policy keeps the last 10 snapshots, the newest snapshot of each of the last 7 days, 4 weeks and 6 "
    "months. Unreferenced objects are then garbage-collected.")

r.h2("3.7 Tools and Technologies")
r.table("Development tools",
        ["Tool", "Purpose", "Reason for choice"],
        [["Python 3.10+", "All modules", "Free, cross-platform, widely taught in Nigerian universities"],
         ["cryptography library", "AES-256-GCM, scrypt", "Audited, maintained implementation"],
         ["psutil", "Host metrics", "Works on Windows and Linux"],
         ["Flask", "Web dashboard", "Small, easy to secure and explain"],
         ["SQLite", "Metrics, alerts, audit", "No server to install or license"],
         ["Playwright / Chromium", "Screenshots during testing", "Repeatable evidence"]],
        widths=[3.5, 4.5, 8])
r.page_break()

# ------------------------------------------------------------ chapter 4
r.h1("CHAPTER FOUR: IMPLEMENTATION, TESTING AND RESULTS")
r.h2("4.1 Implementation Environment")
r.p("The system was developed and tested on Linux with Python 3.11. It also runs on Windows 10 and 11, the "
    "usual operating system on student laptops. The demonstration dataset was produced by simulate.py: a "
    "register of 60,000 students, school fee records with Remita-style references, results for four CMP "
    "courses, twelve lecture note files, and a payroll file for 120 staff (19 files, 9,431,828 bytes).")

r.h2("4.2 User Interface")
r.figure("uniguard_dashboard.png", "UniGuard dashboard showing live metrics, service status, the ransomware "
         "alerts raised during the drill, frozen backups, an anomaly alert and a measured restore time")
r.figure("uniguard_snapshots.png", "Snapshot list with per-snapshot restore (whole snapshot, sub-folder, or "
         "into a separate folder for inspection)")

r.h2("4.3 Test Plan and Results")
r.table("Functional and security test cases",
        ["#", "Test", "Expected result", "Observed result", "Status"],
        [["1", "Initial full backup of 19 files", "Encrypted snapshot created", "Snapshot created, 0.50 s", "Pass"],
         ["2", "Repeat backup with no changes", "No new objects", "0 new objects, 0.09 s", "Pass"],
         ["3", "One results file changed", "Only that file stored", "1 new object, 125.7 KiB, 0.13 s", "Pass"],
         ["4", "Five CSV files encrypted in place, names unchanged", "Snapshot refused, critical alert",
          "Status 'frozen', entropy 7.95 to 7.99 bits/byte reported", "Pass"],
         ["5", "Full ransomware simulation (rename to .locked, ransom note)", "Canary alert, backup frozen",
          "Canary tripped, backup status 'frozen'", "Pass"],
         ["6", "Restore latest clean snapshot in place", "All files identical to originals",
          "19 of 19 files byte-identical (SHA-256), 0.15 s", "Pass"],
         ["7", "One stored object altered by one byte", "Verification fails", "'failed authentication "
          "(tampered)' and critical alert", "Pass"],
         ["8", "Repair from replica", "Good copy restored, verification passes", "1 object repaired, "
          "verification ok", "Pass"],
         ["9", "Wrong passphrase", "Refuse to run", "'Wrong backup passphrase. Refusing to continue.'", "Pass"],
         ["10", "Student portal killed", "Critical alert and automatic restart", "Alert raised, portal back "
          "UP on next cycle", "Pass"],
         ["11", "CPU burst", "Anomaly alert", "'cpu_percent=18.3 is +9.2 std devs from normal'", "Pass"],
         ["12", "Form post without valid CSRF token", "Rejected", "HTTP 400", "Pass"],
         ["13", "Viewer tries to run a backup", "Forbidden", "HTTP 403", "Pass"],
         ["14", "Audit chain check after all tests", "Intact", "Intact", "Pass"]],
        widths=[0.7, 4.3, 3.5, 5.5, 1.3])

r.h2("4.4 Performance Results")
r.table("Measured backup and recovery performance (9.0 MiB dataset)",
        ["Metric", "Value"],
        [["Source data", "9,431,828 bytes (19 files)"],
         ["Stored after compression and encryption", "2,138,358 bytes (77.3% reduction)"],
         ["First full backup", "0.504 s"],
         ["Incremental backup, no changes", "0.091 to 0.093 s"],
         ["Incremental backup, one file changed", "0.133 s, 128,714 bytes stored"],
         ["Deep verification of all snapshots (wall clock, including start-up)", "0.38 s"],
         ["Restore of all 19 files after ransomware (RTO for this dataset)", "0.154 s"],
         ["Data at risk at time of attack (RPO in drill)", "1.6 s since last clean snapshot"],
         ["Configured policy targets", "RPO 60 min, backup every 30 min, monitor every 15 s"],
         ["Repository and each replica size", "2.4 MiB each (3 copies)"]],
        widths=[10, 6])
r.p("The storage reduction is high because CSV and text compress well. Kodali et al. (2026) reported 20 to 23% "
    "on mixed user files, which include already compressed media. The restore time is short because the "
    "dataset is small. For a 200 GB student records server, restore time scales mainly with disk and network "
    "speed, so the ICT unit should re-measure RTO during quarterly drills with real volumes. The detection "
    "time in the drill was immediate because the check ran right after the attack. In normal operation the "
    "detection delay is bounded by the 15-second monitoring interval.")

r.h2("4.5 Discussion")
r.p("The results meet the objectives. The most important finding is test 4. A stealthy attack that encrypts "
    "files without renaming them would, in a naive incremental backup, overwrite the clean history within one "
    "cycle. Integrity gating blocked this, confirming the approach of Amoruso et al. (2026) in a server "
    "setting. Test 8 shows why replicas matter: verification alone only tells the administrator that a backup "
    "is damaged, while the replica allowed automatic repair. Compared with Simili et al. (2021), UniGuard adds "
    "data protection to monitoring and self-healing. Compared with Kodali et al. (2026), it adds replicas, "
    "hash-chained snapshots, role-based access, an audit log and service monitoring.")
r.p("Limitations remain. Entropy checks cannot judge files that are already compressed, such as ZIP or MP4, so "
    "for those UniGuard depends on signature checks and canaries. An attacker with administrator rights on the "
    "backup server could delete the local repository, which is why one replica must be offline or "
    "object-locked. The current version backs up files, so databases must be dumped first.")
r.page_break()

# ------------------------------------------------------------ chapter 5
r.h1("CHAPTER FIVE: SUMMARY, CONCLUSION AND RECOMMENDATIONS")
r.h2("5.1 Summary")
r.p("This project built UniGuard, an automated monitoring, backup and recovery system for university digital "
    "infrastructure. It monitors hosts and services, detects anomalies, restarts failed services, takes "
    "encrypted and de-duplicated backups with three copies, blocks ransomware-encrypted data from the backup "
    "history, verifies and repairs backups, and restores data with measured RTO and RPO. All administrative "
    "actions are recorded in a tamper-evident log.")
r.h2("5.2 Conclusion")
r.p("A reliable recovery capability does not require expensive commercial suites. Standard cryptography, "
    "careful design and regular drills can give a Nigerian university a backup system that survives "
    "ransomware. In testing, UniGuard detected a simulated attack, refused to save encrypted data, and restored "
    "every file byte-for-byte. This addresses the post-event weakness that Olugbile et al. (2025) found in most "
    "Nigerian universities.")
r.h2("5.3 Recommendations")
r.bullets([
    "Adopt a written backup policy approved by Senate: RPO of 1 hour for results and fees, 24 hours for "
    "lecture materials, and an RTO of 4 hours for the student portal.",
    "Keep one replica offline or object-locked, for example a removable disk rotated weekly and stored in "
    "another building.",
    "Run a recovery drill every quarter and present the measured RTO to university management.",
    "Seal a copy of the backup passphrase in two separate physical locations, with access recorded.",
    "Put backup servers on a separate VLAN with no domain trust, so ransomware on staff PCs cannot reach them.",
    "Connect servers to a UPS and enable the battery alert so the ICT unit can take an emergency backup "
    "before the inverter runs out.",
    "Train ICT staff and student workers on phishing and safe Wi-Fi use, as recommended by Yusuf et al. (2026).",
    "Align procedures with NIST CSF 2.0, ISO/IEC 27001:2022 Annex A control 8.13 (information backup) and "
    "the NDPA 2023.",
])
r.h2("5.4 Contribution to Knowledge")
r.bullets([
    "A working, open design that joins monitoring, 3-2-1 encrypted backup, ransomware gating and audited "
    "recovery for low-resource institutions.",
    "Use of HMAC-based object identifiers to obtain de-duplication without leaking file equality.",
    "A reproducible drill that produces RTO, RPO and integrity evidence for management and regulators.",
])
r.h2("5.5 Suggestions for Further Work")
r.bullets([
    "Native PostgreSQL and MySQL hooks with point-in-time recovery from write-ahead logs.",
    "Export of metrics to Prometheus and Grafana for multi-server campuses.",
    "Shamir secret sharing of the passphrase among three officers, so no single person can decrypt backups.",
    "Machine learning detection of ransomware I/O patterns, as in Omopariola et al. (2026).",
])
r.page_break()

# ------------------------------------------------------------ references
r.h1("REFERENCES")
r.references([
    "Aba, J. (2026). Exploring cyberthreats and security of electronic resources in university libraries in South-South, Nigeria. *International Journal of Education, Humanities and Social Science*.",
    "Adamu, U. (2025). Enhanced cybersecurity resilience model for sensitive data protection in Nigerian tertiary institutions: A review. *Journal of Systematic and Modern Science Research*.",
    "Amoruso, E. L., et al. (2026). Integrity-gated file monitoring for ransomware resilience and real-time recovery. *2026 International Conference on Smart Applications, Communications and Networking (SmartNets)*. IEEE.",
    "Baek, S., et al. (2021). SSD-assisted ransomware detection and data recovery techniques. *IEEE Transactions on Computers*.",
    "Bajpai, M. (2022). Automating monitoring and incident management with Prometheus, Grafana, and Google Cloud Pub/Sub. *International Journal of Science and Research*.",
    "Dotasara, M., et al. (2022). MDAS_DBRCC: Data backup and recovery technique in cloud computing for education industry. *International Journal on Recent and Innovation Trends in Computing and Communication*.",
    "Edet, N., et al. (2026). Cybersecurity and information management in digital libraries: Emerging challenges for Nigerian academic institutions. *Global Journal of Modern Research and Emerging Trends*.",
    "Farouk, S., et al. (2024). Enhancing cybersecurity in Nigeria: A proposed risk management framework for universities. *2024 International Conference on Science, Engineering and Business for Driving Sustainable Development Goals (SEB4SDG)*. IEEE.",
    "Ganesan, P. (2024). Cloud-based disaster recovery: Reducing risk and improving continuity. *Journal of Artificial Intelligence & Cloud Computing*.",
    "Ilau, M.-C., et al. (2025). Modelling and simulating organizational ransomware recovery: Structure, methodology, and decisions. *Journal of Cybersecurity*.",
    "Kasinadhuni, B. (2026). From detection to action: AI-driven anomaly detection and root cause synthesis for cloud infrastructure operations. *International Journal of AI, BigData, Computational and Management Studies*.",
    "Kodali, A., et al. (2026). Automatic ransomware-resilient encrypted backup system using SHA-256 change detection and AES-256-GCM encryption. *2026 3rd International Conference on Research Methodologies in Knowledge Management, Artificial Intelligence and Telecommunication Engineering (RMKMATE)*. IEEE.",
    "Kumar, B., et al. (2026). Artificial intelligence driven approach for securing backup data and enhancing cyber resilience in sustainable smart infrastructure. *Scientific Reports*.",
    "Leonard, S., et al. (2026). Assessing the impact of cybercrime and digital forensic preparedness on data security management in Nigerian public universities: A literature review. *Journal of Digital Security and Forensics*.",
    "Lysetskyi, Y., et al. (2025). Choosing an effective data backup and recovery strategy. *Mathematical Machines and Systems*.",
    "Muthoni, S., et al. (2021). Infrastructure as code for business continuity in institutions of higher learning. *2021 International Conference on Electrical, Computer and Energy Technologies (ICECET)*. IEEE.",
    "Olugbile, O. H., et al. (2025). Towards a standard framework for cybersecurity readiness for Nigerian universities. *International Journal of Applied Mathematics, Sciences, and Technology for National Defense*.",
    "Omopariola, V., et al. (2026). Anti ransomware file backup system. *Nature Journal of Emerging Sciences Technologies and Innovations*.",
    "Onche, V. O., et al. (2023). BYOD adoption and information-security risk in university administrative offices: Evidence from Nigerian federal universities. *International Journal of Multidisciplinary Research and Growth Evaluation*.",
    "Plaka, R. (2022). Backup & data recovery in cloud computing: A systematic mapping study. *Ingenious*.",
    "Pragathi, B. C., et al. (2024). Implementing an effective infrastructure monitoring solution with Prometheus and Grafana. *International Journal of Computer Applications*.",
    "Rafiq, A., et al. (2025). AI and IoT-driven monitoring and visualisation for optimising MSP operations in multi-tenant networks: A modular approach using sensor data integration. *Sensors*.",
    "Sai, K. (2024). Enhanced visibility for real-time monitoring and alerting in Kubernetes by integrating Prometheus, Grafana, Loki, and Alerta. *International Journal of Scientific Research in Engineering and Management*.",
    "Simili, E., et al. (2021). A hybrid system for monitoring and automated recovery at the Glasgow Tier-2 cluster. *EPJ Web of Conferences*.",
    "Tajudeen, O. T., et al. (2026). A validated framework for ransomware resilience: Mitigation, recovery, and empirical evaluation. *UMYU Scientifica*.",
    "Tarasenko, S., et al. (2025). Science mapping analysis of challenges surrounding cloud universities and their impact on the resilience of higher education. *Knowledge and Performance Management*.",
    "Tatineni, S. (2023). Cloud-based business continuity and disaster recovery strategies. *International Research Journal of Modernization in Engineering Technology and Science*.",
    "Varshney, P., et al. (2026). A governance-oriented cyber recovery framework for ransomware preparedness and resilience. *EDPACS*.",
    "Vinisha, J., et al. (2025). Automated disaster recovery architecture for educational institutions web infrastructure using hybrid cloud. *2025 2nd International Conference on Artificial Intelligence and Knowledge Discovery in Concurrent Engineering (ICECONF)*. IEEE.",
    "Yunisa, B. (2025). Operation of cyber security in tertiary institution in Nigeria: Problems and way forward. *Academic Journal Research*.",
    "Yusuf, T., et al. (2026). Cybersecurity threat awareness in Wi-Fi and hotspot usage among university students: Evidence from the University of Ilesa, Ilesa, Osun State, Nigeria. *Journal of Innovative Social Science and Humanities Research*.",
    "Zhang, X., et al. (2026). An enhanced intelligent monitoring and alerting system based on metric analysis. *2026 6th International Symposium on Computer Technology and Information Science (ISCTIS)*. IEEE.",
])
r.h2("Standards and Legal Instruments Consulted")
r.references([
    "Federal Republic of Nigeria. (2023). *Nigeria Data Protection Act, 2023*. Nigeria Data Protection Commission.",
    "International Organization for Standardization. (2022). *ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection: Information security management systems: Requirements*. ISO.",
    "National Institute of Standards and Technology. (2024). *The NIST Cybersecurity Framework (CSF) 2.0* (NIST CSWP 29). NIST.",
])
r.page_break()

r.h1("APPENDIX A: SOURCE CODE STRUCTURE")
r.table("UniGuard source files", ["File", "Purpose"],
        [["common.py", "Configuration, SQLite access, alert channels, password hashing, audit chain"],
         ["backup_engine.py", "Key derivation, encryption, snapshots, replication, verify, repair, restore, prune"],
         ["ransomware_guard.py", "Canary files, entropy and signature inspection"],
         ["monitor.py", "Metrics, service checks, anomaly detection, RPO check, self-healing"],
         ["app.py", "Flask dashboard and background scheduler"],
         ["cli.py", "Command line interface for cron or Task Scheduler"],
         ["simulate.py", "Demo data, demo portal, outage, ransomware simulation and recovery drill"],
         ["config.json", "Policy settings: thresholds, RPO, retention, replicas, alert channels"]],
        widths=[4, 12])
r.p("The full source code and the step-by-step implementation guide are in the project folder "
    "project1-uniguard (README.md).")

r.save(OUT)
print("wrote", OUT)
