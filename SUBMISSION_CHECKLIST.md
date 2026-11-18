# SUBMISSION_CHECKLIST — what must exist, and when

One page, ordered by clock. Detail lives in `SUBMISSION.md`; the recording script lives in
`VIDEO_GUIDE.md`. Deadlines are **IST**: build freeze **Thu 19 Nov 10:00**, blind-test CSVs pushed
**before 12:00 noon**.

---

## 1 · The four things you actually hand in

> The challenge email asks for **two links** (public repo, hosted app) via the *Submission link* in the
> email, and the **three CSVs** in `submission/`. It does **not** ask for a video — record one only if
> the submission form asks. It writes "Wed 19 Nov" for the build deadline, but 19 Nov 2026 is a
> **Thursday**, matching the blind test it schedules: treat everything as Thu 19 Nov.

| # | Artifact | Where it must be | Deadline |
|---|---|---|---|
| 1 | **Public GitHub repo** (no task data) — done: `github.com/Saurabhyadav0/cantill-fullstack-intern-task` | URL in the submission form + `README.md` → *Repository* | 10:00 Thu |
| 2 | **Hosted app**, stays up through review | URL in the submission form + `README.md` → *Hosted demo* | 10:00 Thu |
| 3 | **Walkthrough video** — *only if the form asks* | unlisted link in `README.md` → *Demo video* | 10:00 Thu |
| 4 | **Three blind-test CSVs** in `submission/` | `submission/<name>__run1.csv`, `__run2.csv`, `__preferred.csv` | 12:00 Thu |

Plus, already required inside the repo: `DECISIONS.md` (judgment), `APPROACH.md` (AI tools used),
`README.md` (run instructions + links), green `pytest`, and the app itself.

> **The trap:** the video and hosted links live in `README.md`, and `README.md` is a commit. After
> 10:00 Thursday the only commit allowed is the blind-test CSVs. **Record and paste both links before
> the freeze** — Wednesday night, or Thursday 09:00–09:45.

---

## 2 · Before the freeze — do these now

### 2.1 Tests and repo hygiene

```bash
.venv/bin/python -m pytest                                   # 25 passed

# no task data tracked (only data/README.md may appear)
git ls-files | grep -E '^(data/|docs/policy-v5)' | grep -v '^data/README.md'

# no secrets tracked
git ls-files | grep -E '^\.env'

# nothing uncommitted when you freeze
git status --short
```

Expected: `25 passed`; the two `grep`s print **nothing**; `git status` is clean.

### 2.2 Hosted app: deploy, then prove it

```bash
# local build, with data/ and docs/policy-v5.json present
docker build -t ghcr.io/<user>/corvo-prpo:latest .
docker run -p 8000:8000 ghcr.io/<user>/corvo-prpo:latest
```

Push to a **private** registry and deploy (Render → *Deploy an existing image*, port `8000`, health
check `/api/health`), or run `docker compose up -d --build` on a VPS. Full options: `SUBMISSION.md` §5.

Then, **on the deployed URL**, not locally:

- [ ] `/api/health` returns `{"ok": true}`
- [ ] `/api/meta` returns `"ready": true`
- [ ] **Process sample batch** → tiles read `151` / `₹1,12,14,692` / `₹5,12,60,623` / `84`
- [ ] **decisions.csv** downloads with 186 data rows and the exact §6 columns
- [ ] **preferred.csv** downloads and has `item_code,rank,supplier_id,reference_price`
- [ ] the URL is pasted in `README.md` and the link opens in a private browser window

> Free tiers sleep. Open the URL on the morning of the 19th to wake it, and again before you submit.

### 2.3 Video

- [ ] recorded against a **clean** `api/app.db` (policy v5.0 first, per `VIDEO_GUIDE.md` §0.2)
- [ ] shows v5.0 → v5.1 → v5.2 and the route counts moving (60/39/4 → 72/27/4 → 72/20/11)
- [ ] under 8 minutes, 1080p, audio audible on laptop speakers
- [ ] uploaded unlisted, link tested in a private window
- [ ] link pasted in `README.md` → *Demo video* **and** `SUBMISSION.md` §1

### 2.4 Docs that are graded on their own

- [ ] `DECISIONS.md` has D-0 … D-21, each with what you noticed, decided, and why
- [ ] `APPROACH.md` lists the AI tools actually used and how
- [ ] `README.md` has: one-command run, hosted link, video link, architecture paragraph
- [ ] `SUBMISSION.md` §1 table reflects reality (no stale ❌ rows)

### 2.5 Freeze the build

```bash
git status --short              # must be clean
git log --oneline -1            # note this commit as the frozen build
git tag -a build-freeze -m "frozen build for blind test" && git push origin build-freeze
```

Tagging is optional; **the clean tree at 10:00 is not.**

---

## 3 · Freeze → 12:00 (the only work allowed)

No code changes. No `.env` edits. No deploys. The only accepted commit is the CSVs.

1. **Run 1** — open the app, upload the new batch, keep policy **v5.0**, **decisions.csv** →
   `submission/<name>__run1.csv`.
2. **Run 2** — role **Procurement** → **Policy (data)** → paste the amendment → **Preview changes** →
   **Approve & activate** → role **Buyer** → reprocess the **same** batch → **decisions.csv** →
   `submission/<name>__run2.csv`.
3. **Preferred** — set the *as of* date they specify → **preferred.csv** →
   `submission/<name>__preferred.csv`.

Then verify, before pushing:

```bash
# 1. Run 1 vs Run 2 must differ — print how many lines changed route
python - <<'PY'
import csv
def load(p): return {(r['pr_no'], r['pr_line']): r for r in csv.DictReader(open(p))}
a, b = load('submission/<name>__run1.csv'), load('submission/<name>__run2.csv')
changed = [(k, a[k]['route'], b[k]['route']) for k in a if a[k]['route'] != b[k]['route']]
print(len(changed), 'lines changed')
for c in changed[:15]: print(c)
PY

# 2. No Blocked/Inactive supplier may appear anywhere (explicitly penalised, §5.7)
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

# 3. Schema check — columns must match CONTEXT.md §6 exactly
head -1 submission/<name>__run1.csv
```

Expected: run 1 and run 2 differ (a non-zero count, concentrated where the amendment bites);
`0 violations` for both files; 186 data rows for the sample-sized batch (more/fewer for the real one —
it should equal the lines in the batch you were given).

```bash
git add submission/ && git commit -m "submission: blind-test runs" && git push
```

- [ ] pushed **before 12:00 noon**
- [ ] the app is still up, and you did not commit anything else

---

## 4 · Go / no-go

| Check | Evidence | ✓ |
|---|---|---|
| Public repo URL in `README.md` | opens logged-out | [ ] |
| No task data in the repo | §2.1 `grep` prints nothing | [ ] |
| Hosted link live and warm | sample batch runs on it | [ ] |
| Video link works unlisted | opens in a private window | [ ] |
| Video shows the live policy change | route counts move on camera | [ ] |
| `pytest` green | 25 passed | [ ] |
| `DECISIONS.md`, `APPROACH.md` current | D-0 … D-21, tools list | [ ] |
| Three CSVs pushed before noon | `git log origin/main -1` shows only the CSV commit | [ ] |
| Run 1 ≠ Run 2 | §3 diff prints changed lines | [ ] |
| No Blocked/Inactive suppliers | 0 violations in both CSVs | [ ] |
| No commits after the freeze | `git log build-freeze..main --stat` shows only `submission/` | [ ] |

---

## 5 · What is deliberately **not** submitted

- `data/` — the kit's CSVs and PDFs (gitignored; `data/README.md` explains placement).
- `docs/policy-v5.json` — the policy as data (gitignored; the hosted image carries it).
- `api/app.db` — runtime state (gitignored).
- `.env` — no secret is required to run the app; the optional `ANTHROPIC_API_KEY` never leaves your
  machine (and `anthropic` is not installed, so the heuristic parsers are what actually run).

Pushing any of these breaks the brief's "public repo must not contain the task data" rule and is
graded against you. If you ever see them in `git status` as tracked, stop and fix `.gitignore` —
`git ls-files | grep -E '^(data/|docs/policy-v5)'` must stay empty.

---

## 6 · If it goes wrong

| Situation | What to do |
|---|---|
| Hosted app asleep / 502 | open it 10 minutes before review and let it wake; keep a terminal copy of the runbook for yourself |
| Uploaded the wrong batch | reprocess and re-export; the CSV must match the batch they sent |
| Amendment preview won't parse | build the same change in **Advanced — apply structured ops**, approve, reprocess — the scored output is the CSV, not the typing |
| Run 1 and Run 2 identical | the amendment never activated (wrong role, or you approved after exporting) — approve, reprocess, re-export run 2 |
| A Blocked/Inactive supplier appears | a real engine bug; fix in code only **before** 10:00, otherwise report it in `DECISIONS.md` — never hand-edit the CSV |
| You already pushed code after 10:00 | do not force-push history. Say so plainly in the submission email; a reverted history is worse than a disclosed one |
