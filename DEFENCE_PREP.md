# CMP 468 Presentation and Defence Preparation

## 1. Slide outline (10 to 12 minutes per project)

### Project 1: VarsityShield
1. Title, your name, matric number.
2. Problem in one picture: a Nigerian university loses a semester of results to ransomware. Cite Olugbile et al. (2025): 65% of 20 universities in the lowest readiness tier.
3. Aim and 7 objectives.
4. Literature gap table (from Chapter 2, Table 3).
5. Architecture diagram (Chapter 3).
6. Security design: AES-256-GCM, scrypt, HMAC object ids, hash-chained snapshots, canaries, entropy gating.
7. Live demo (README Part B, 6 minutes).
8. Results table: 77.3% storage reduction, 0.09 s incremental, RTO 0.15 s, 14 of 14 tests passed.
9. Mapping to CMP 468 course outline.
10. Recommendations and limitations.

### Project 2: Zaman Lafiya
1. Title.
2. Problem: Nnaji et al. (2022), conflict severity raises food insecurity in 401 households. Late warning, weak response, informants at risk.
3. Aim and objectives.
4. Literature gap table.
5. Architecture and data layers.
6. Risk model: features, rule index formula, random forest, time split.
7. Security: encryption of informants, signed GPS pings, RBAC, audit chain.
8. Live demo (README Part B, 7 minutes).
9. Results: AUC 0.659 vs 0.611 baseline, NDVI most important, 3 encroachments and 5 deviations detected live.
10. Ethics, limitations, recommendations.

Tip: record a screen video of each demo the night before. If the projector laptop fails, play the video.

## 2. Likely questions and short answers

### VarsityShield
**Why AES-GCM instead of AES-CBC?**
GCM gives encryption and an authentication tag together. A single changed byte makes decryption fail, so tampering is detected. CBC alone does not detect tampering.

**Why not name objects by SHA-256 of the content?**
Then anyone who sees the repository can check whether a known file (for example a leaked payroll) is stored. HMAC with a secret key gives de-duplication without that leak.

**What happens if ransomware hits the backup server itself?**
Objects are read-only, snapshots are hash-chained, and replicas sit on another disk and offsite. The policy requires one offline or object-locked copy. An attacker with admin rights can delete the local repository, but not the offline copy.

**Entropy checks fail on ZIP and JPEG files. How do you handle them?**
For those formats VarsityShield checks the file signature (for example `PK` for DOCX, `%PDF` for PDF) and relies on canary files.

**How did you measure RTO and RPO?**
`simulate.py drill` times the restore (RTO) and the gap between the last clean snapshot and the attack (RPO), and confirms all files are byte-identical by SHA-256.

**What if the admin forgets the passphrase?**
Backups are lost. That is why the recommendations require a sealed copy in two places. Future work: Shamir secret sharing among three officers.

**Is 0.15 s realistic?**
For 9 MB, yes. For a 200 GB server, restore time depends on disk and network speed, so the ICT unit should measure it during quarterly drills.

**Which standard does this follow?**
NIST CSF 2.0 Recover function, ISO/IEC 27001:2022 control 8.13 (information backup), and the NDPA 2023.

### Zaman Lafiya
**Your data is synthetic. Why should we trust the model?**
The synthetic data validates the pipeline. The `import-acled` command loads real ACLED events and `train` re-evaluates with the same time-based split. I report the honest AUC with a naive baseline instead of accuracy.

**Why is AUC only 0.659?**
Predicting a specific LGA's incidents 7 days ahead is hard. Goodman et al. (2024) got about 0.75 for a yearly horizon with satellite images. The model still beats the naive baseline (0.611), and the rule layer adds real-time signals the model cannot see.

**Why combine rules with machine learning?**
Rules are explainable and react instantly to herds inside farms. The model captures patterns from history. Averaging them gives both.

**How do you stop fake reports?**
Rate limit per number per hour, honeypot field against bots, analyst verification, credibility score per sender, and unverified reports count at only 0.6 weight.

**How do you protect informants?**
Phone numbers are encrypted with Fernet. A keyed HMAC pseudonym is used for counting and credibility. Only admins can reveal a number, with a reason, and the reveal is written to the hash-chained audit log.

**Can someone send fake herd locations?**
Each ping is signed with HMAC-SHA256 over the timestamp and body. Unsigned or older-than-5-minute pings are rejected (HTTP 401). This stops forgery and replay.

**Will herders accept tracking?**
It must be voluntary and agreed with herders' associations. Herders benefit too: route guidance, water point status, and evidence against false accusations.

**Doesn't this stigmatise one ethnic group?**
Reports describe events (crop damage, theft, threats), not ethnicity. Alerts go to both farmer and herder leaders in their languages, and verification is required before escalation.

**Why SQLite and not PostGIS?**
SQLite needs no server for the prototype. The geometry functions are simple and documented. PostGIS is the recommended upgrade for statewide use.

**Why is loading a pickle file a security issue?**
Unpickling can execute code. Zaman Lafiya stores the model's SHA-256 at training time and refuses to load a file whose hash differs.

## 3. Checklist for the day
- [ ] Both projects run from a fresh folder on the presentation laptop (do Part A of each README).
- [ ] Changed default passwords.
- [ ] Keys and passphrase written on paper.
- [ ] Two terminals ready per project, variables already set.
- [ ] Phone hotspot ready for map tiles.
- [ ] Backup video of each demo.
- [ ] Reports printed and bound. Right-click the table of contents in Word and choose Update Field before printing.
- [ ] Replace the placeholders on the title page: university, faculty, name, matric number, lecturer.
