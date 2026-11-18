# SUBMISSION — what to hand in, and how

One page that maps the brief's requirements to what exists in this repo, plus the Thursday
runbook and the things only you can do (public repo, hosted link, video, the three CSVs).

Deadlines are IST: **build freeze Thu 19 Nov 10:00**, **blind-test files pushed before 12:00 noon**.
(The email writes "Wed 19 Nov" for the build deadline, but 19 Nov 2026 is a Thursday and the blind
test it schedules is also dated Thu 19 Nov — so the whole sequence is treated as Thu 19 Nov.)

The email asks for exactly: **public repo URL**, **hosted app URL**, and the **three blind-test CSVs**
in `submission/` — plus `DECISIONS.md` and `APPROACH.md` inside the repo. A walkthrough video is
*not* asked for by the email; `VIDEO_GUIDE.md` stays ready in case the submission form requests one.

> Day-of companion: **`SUBMISSION_CHECKLIST.md`** — the required artifacts, their deadlines, the
> pre-freeze git/deploy checks and the go/no-go table. Recording script: **`VIDEO_GUIDE.md`**.

---

## 1 · Requirement → where it is → status

| The brief asks for | Where it lives | Status |
|---|---|---|
| Web app: chat intake + API + persistence | `web/`, `api/` (FastAPI + SQLite) | ✅ done |
| Policy-driven decision engine (§1–§8) | `engine/` (pure, no web/DB imports) | ✅ 14 worked decisions + 3 rankings as tests |
| Policy **as data**, versioned, approvable | `docs/policy-v5.json` schema, `api/amend.py`, Policy tab | ✅ limits, windows, added/removed rules, plant-specific rule kind |
| Chat UX: asks, never invents items | `api/chat.py`, Chat intake tab | ✅ disambiguation + NEW flagging + slot filling |
| Buyer workspace: decision + why + act | Buyer tab + drawer | ✅ approve / override-with-reason / ranking explanation |
| API + exports in the scored schema | `/api/process-batch`, `/api/export/decisions.csv`, `/api/export/preferred.csv` | ✅ |
| Contracts incl. PDF-only | Contracts tab, `data/contracts/pdf_only_contracts.json` | ✅ |
| Preferred supplier list + ranking | `engine/core.py` §6, drawer panel, CSV | ✅ formula + reasoning in `DECISIONS.md` D-10 |
| Tests | `tests/` — `pytest` → **25 passed** | ✅ |
| `DECISIONS.md` (judgment) | 22 recorded decisions (D-0 … D-21) | ✅ |
| `APPROACH.md` (AI tools used) | tool list + architecture | ✅ |
| **Public GitHub repo, no task data** | https://github.com/Saurabhyadav0/cantill-fullstack-intern-task — `.gitignore` blocks `data/`, `docs/policy-v5*.json`, `*.csv`, `*.pdf`; verified public and verified no data file in any commit | ✅ done |
| **Hosted link that stays up** | `README.md` → *Hosted demo* | ❌ you must deploy (steps in §5) |
| Walkthrough video *(not requested by the email)* | script in `VIDEO_GUIDE.md` | ⚠️ only if the form asks |
| **3 blind-test CSVs in `submission/`** | `submission/` (`.gitignore` now allows `submission/*.csv`) | ⏳ Thursday, §4 |

---

## 2 · Folder audit — everything the task ships/needs

```
engine/        models, matching, policy interpreter, core pipeline, loaders   (pure Python)
api/           main (routes + UI), db (sqlite), amend (policy ops), chat (NL intake)
web/           index.html — single-file React app, no build step
docs/          README.md (policy schema) + policy-v5.json (gitignored, local)
data/          README.md (committed) + kit CSVs/PDFs (gitignored, local)
   master_data/ item_master, supplier_master, po_history, plants
   contracts/   contract_register, contract_lines, pdf_only_contracts.json, pdf/
   pr_batches/  sample_pr_batch.csv (186 lines)
tests/         test_worked_examples.py, test_api.py, conftest.py
submission/    blind-test CSVs go here Thursday + README
Dockerfile · docker-compose.yml · Makefile · requirements.txt · pytest.ini · .env.example
CONTEXT.md · FEATURES.md · TASK.md · CLAUDE.md · DECISIONS.md · APPROACH.md
README.md · SUBMISSION.md · VIDEO_GUIDE.md
```

Verify locally in 30 seconds:

```bash
.venv/bin/python -m pytest            # 25 passed
.venv/bin/uvicorn api.main:app --port 8000   # UI at http://localhost:8000
```

---

## 3 · Before you push the public repo

```bash
# 1. tests green
.venv/bin/python -m pytest

# 2. no task data is tracked (should print nothing)
git ls-files | grep -E '^(data/|docs/policy-v5)' | grep -v '^data/README.md'

# 3. no secrets are tracked
git ls-files | grep -E '^\.env'

# 4. submission folder is clean of the sample outputs you tested with
ls -1 submission/
```

Then: create the **public** repo, push, and put its URL in `README.md`.

> The `submission/*.csv` outputs *are* deliverables and must be committed — the `.gitignore`
> deliberately re-allows them even though kit CSVs are ignored.

---

## 4 · Blind-test runbook (Thu 19 Nov, 10:00–12:00 — no code changes)

Use the deployed app or a local run; either is allowed. Replace `<name>` with your name.

### Run 1 — new batch under v5.0 (10:00–11:00)
1. **Buyer workspace → Upload batch CSV** → pick the new batch file.
2. Confirm the header shows **policy v5.0**.
3. **decisions.csv** → save as `submission/<name>__run1.csv`.

### Run 2 — amendment through the app, then reprocess (11:00–11:45)
4. Role → **Procurement** → **Policy (data)**.
5. Paste the amendment text → **Preview changes**.
   - If the preview doesn't match the amendment (or says it couldn't parse), open
     **Advanced — apply structured ops** and express the amendment as ops
     (`set_param` / `set_rule_value` / `add_rule` / `remove_rule` — see `docs/README.md`).
6. **Approve & activate** → note the new version.
7. Role → **Buyer** → reprocess the **same** batch → header shows the new version.
8. **decisions.csv** → save as `submission/<name>__run2.csv`.
9. **Preferred suppliers** as of the date they give → `preferred.csv` →
   `submission/<name>__preferred.csv`.

### Verify before pushing (5 minutes)
```bash
# run1 vs run2: the amendment must have changed something
python - <<'PY'
import csv
def load(p): return {(r['pr_no'], r['pr_line']): r for r in csv.DictReader(open(p))}
a = load('submission/<name>__run1.csv'); b = load('submission/<name>__run2.csv')
changed = [(k, a[k]['route'], b[k]['route']) for k in a if a[k]['route'] != b[k]['route']]
print(len(changed), 'lines changed')
for c in changed[:15]: print(c)
PY

# no Blocked/Inactive supplier anywhere (severely penalised)
python - <<'PY'
import csv
banned = {r['supplier_id'] for r in csv.DictReader(open('data/master_data/supplier_master.csv'))
          if r['status'] in ('Blocked', 'Inactive')}
for fn in ('submission/<name>__run1.csv', 'submission/<name>__run2.csv'):
    rows = list(csv.DictReader(open(fn)))
    bad = [r for r in rows if r.get('supplier_id') in banned
           or banned & set((r.get('suggested_supplier_ids') or '').split(';'))]
    print(fn, len(rows), 'rows,', len(bad), 'violations')
PY
```

10. `git add submission/ && git commit -m "submission: blind-test runs" && git push` — **before 12:00**.
11. Keep the hosted app up; reviewers may re-run it.

---

## 5 · Hosting (the repo must not contain the task data)

The app needs `data/` and `docs/policy-v5.json` at runtime, but the public repo may not ship them.
Two workable patterns:

### Option A — private container image (recommended)
```bash
# locally, with data/ and docs/policy-v5.json present
docker build -t ghcr.io/<github-user>/corvo-prpo:latest .
docker run -p 8000:8000 ghcr.io/<github-user>/corvo-prpo:latest   # sanity check

# push to a PRIVATE GitHub Container Registry package
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
docker push ghcr.io/<github-user>/corvo-prpo:latest
```
Then on **Render**: *New → Web Service → Deploy an existing image*, image
`ghcr.io/<github-user>/corvo-prpo:latest`, add the registry credential, port `8000`,
health check path `/api/health`. The image carries the data; the repo stays clean.

### Option B — small VPS with docker compose + a volume
```bash
rsync -av data docs/policy-v5.json <user>@<host>:~/corvo/
ssh <user>@<host> 'cd ~/corvo && docker compose up -d --build'
```
Put nginx/Caddy in front for HTTPS, or use the platform's proxy.

### Option C — tunnel from your machine (backup only)
```bash
cloudflared tunnel --url http://localhost:8000   # or: ngrok http 8000
```
Only acceptable if it stays up through review — the hosted link must work when they click it.

After deploying: open the link, process the sample batch once, and download both CSVs to prove the
deployed instance has data and the policy seeded.

---

## 6 · Final checklist (tick before you submit)

The same checks, ordered by clock, are in **`SUBMISSION_CHECKLIST.md`**.

- [ ] `pytest` → 25 passed
- [ ] Public repo pushed; **no** `data/` CSVs, PDFs or `policy-v5*.json` in it
- [ ] `README.md` has the **repo link**, **hosted link**, and **video link**
- [ ] Hosted app loads, processes a batch, exports both CSVs
- [ ] `APPROACH.md` lists the AI tools used (Claude Code / Claude API as applicable)
- [ ] `DECISIONS.md` current (D-0 … D-21)
- [ ] `submission/<name>__run1.csv`, `_run2.csv`, `_preferred.csv` committed **before 12:00**
- [ ] Run 1 vs Run 2 differ; no Blocked/Inactive supplier anywhere
- [ ] No commits after the 10:00 freeze
