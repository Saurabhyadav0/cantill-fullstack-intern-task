# VIDEO_GUIDE — the recording script (one rehearsal, one take, ~7:35)

Round 2 asks for a short walkthrough of the app, a look at `DECISIONS.md`, and **a change made live**.
This is the script: exact clicks, exact words, the two live policy changes, and the numbers that must
appear on screen. Record it **before Thu 19 Nov 10:00 IST** — after the freeze you must not push code,
and the video link has to be in `README.md` before then.

> Every figure below was produced by running the shipped sample batch through the engine
> (186 PR lines → 151 requirements, policy v5.0). If a number on screen differs, you are not on v5.0
> with the kit data — reset (§0.2) instead of recording a wrong number.

---

## 0 · Before you hit record

### 0.1 Start the app

```bash
cd ~/Desktop/Cantill-FullStack-Intern-Task
. .venv/bin/activate
uvicorn api.main:app --port 8000
# then open http://localhost:8000
```

Port already taken? Find the owner and kill **that PID** (never kill by name pattern):

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN     # note the PID in the second column
kill <PID>
```

### 0.2 Reset to a clean policy — do this before every take

```bash
rm -f api/app.db                     # stop uvicorn first (Ctrl-C)
# restart uvicorn → v5.0 is reseeded; no drafts, versions, overrides or runs left over
```

The whole story is **v5.0 → v5.1 → v5.2 with no deploy**. Leftover versions from a rehearsal make that
story false on camera, and the version chip in the top bar exposes it.

### 0.3 Screen and audio

| Thing | Setting |
|---|---|
| Recorder | macOS `Cmd+Shift+5` → *Record Selected Portion*, or OBS at 1920×1080 / 30 fps |
| Window | Browser at 1440×900 or larger; below 960 px the sidebar becomes a top bar |
| Browser | `Cmd +` to ~110 %, one tab, bookmarks bar hidden (`Cmd+Shift+B`) |
| Cursor | Move slowly, park it on whatever you are naming, never circle |
| Audio | Quiet room, built-in mic, 10-second test first; say "check, check" and play it back |
| Noise | Do Not Disturb on, Slack/WhatsApp closed, phone silent |

### 0.4 60-second pre-flight (no recording yet)

- **Buyer workspace → Process sample batch** → tiles read `151` / `₹1,12,14,692` / `₹5,12,60,623` / `84`.
- **REQ-0001** → `Spot PO`, `₹1,31,676`, basis `recent PO · 3.1b`, supplier `S020`, `PO-0001`.
- **Policy (data)** with role **Procurement** → chip *Raise the Spot PO limit to 3,00,000* →
  **Preview changes** → the draft says **Rs 200,000 → Rs 300,000**.
- Then reset (§0.2) so the take starts clean. Do not record over a half-played state.

---

## 1 · Running order

| Time | Section | What is on screen |
|---|---|---|
| 0:00 | Cold open | Chat intake |
| 0:20 | Chat: free text → draft PR | Chat + draft panel |
| 1:05 | Chat: ambiguity and a NEW item | Chat |
| 1:35 | Process the sample batch | Buyer workspace |
| 2:05 | Why this decision | Decision drawer, REQ-0001 |
| 2:55 | Why this supplier | Preferred suppliers panel, then Approve |
| 3:25 | Filters and the two exports | Buyer workspace header |
| 3:50 | **Live change 1** — a limit as data | Policy (data), v5.1 |
| 4:40 | Proof it changed decisions | Buyer workspace, REQ-0143 |
| 5:20 | **Live change 2** — a new kind of rule | Policy (data), v5.2 |
| 6:00 | Proof again | Buyer workspace, RFP filter |
| 6:25 | Contracts and audit | Contracts, Audit trail |
| 6:55 | `DECISIONS.md` | Editor |
| 7:20 | Tests and close | Terminal |

---

## 2 · The script

> **SAY** lines are written to be spoken. Do not read the **[DO]** lines out loud.

### 0:00 — Cold open (20 s)

**[DO]** Open `http://localhost:8000`, landing on **Chat intake**. Point at the policy chip in the top bar.

> **SAY** "This is Corvo's procurement app. Employees raise purchase requests by chatting, and the
> system decides whether to place a purchase order or raise a sourcing request — by following the
> procurement policy stored as data. The decision engine is a pure Python package; this is a FastAPI
> service serving a small React UI. The chip up here shows the policy version every decision is using:
> v5.0."

### 0:20 — Chat: free text becomes a draft PR (45 s)

**[DO]** Click the suggestion chip **“need 200 nitrile gloves for Chakan by next Friday”**.

> **SAY** "One sentence, no item code. It matched *nitrile gloves* to ITM-1048 — by description, not
> by code — and filled quantity 200, plant CHK1, and the need-by date from 'next Friday'. The panel on
> the right is the PR draft: every field it could derive is filled, and it only asks for what is
> genuinely missing."

**[DO]** Point at the reply, then at the right-hand checklist.

> **SAY** "Nothing was invented. If it cannot match the item it says so rather than guessing a code."

**[DO]** Click **Create PR**.

> **SAY** "That's a PR in the buyer's queue — and the draft clears, ready for the next request."
> *(the toast and the bot message both show the new PR number)*

### 1:05 — It asks instead of guessing (30 s)

**[DO]** Type `2 ball bearings for Pune by 2026-12-01` → Enter.

> **SAY** "Two bearing items score within six hundredths of each other, so it shows the candidates and
> asks — it does not pick one for me."

**[DO]** Click the first candidate (`ITM-1022`).

> **SAY** "And something that isn't in the master…"

**[DO]** Type `flux capacitor 2 units for Pune` → Enter.

> **SAY** "…is flagged as a NEW item and will go to sourcing. Under §1.2 a new item is never clubbed
> and never gets supplier suggestions — inventing a supplier here is exactly what the policy forbids."

### 1:35 — Process the sample batch (30 s)

**[DO]** Click **Buyer workspace** → **Process sample batch**.

> **SAY** "This is the kit's 186-line PR batch. Clubbing turns it into 151 requirements — same item,
> same plant, inside the policy's 14-day and ±7-day windows. 96 requirements end in a purchase order
> for ₹1,12,14,692, 55 go to sourcing for ₹5,12,60,623, and those 96 PO requirements consolidate into
> just 84 POs. Note the policy version on the run: v5.0."

### 2:05 — Why this decision (50 s)

**[DO]** Click the first row, **REQ-0001**. The drawer opens on the right.

> **SAY** "Every requirement explains itself. This one is a Spot PO under clause 5.4 — value
> ₹1,31,676, below the two-lakh limit, from a supplier we bought this item from in the last year. The
> value is not a guess: it's the most recent PO price under clause 3.1(b), and the drawer names the
> clause. Supplier S020 at the reference price, consolidated into PO-0001, and the decision records the
> policy version it was judged under — v5.0."

**[DO]** Scroll the drawer: lines → value basis → supplier/PO → clause.

> **SAY** "That chain — matched item, clubbed lines, chosen contract or PO, the rule that fired, the
> version — is what §8 asks a decision to record, and it's what an auditor would need."

### 2:55 — Why this supplier (30 s)

**[DO]** Scroll to **Preferred suppliers**.

> **SAY** "This is §6: every Active supplier that sold us the item in 548 days or held a contract. The
> ranking is not a black box — frequency, recency, contract, on-time and quality, each scored and
> weighted, and the weights themselves live in the policy document. The supplier this decision
> actually used is marked."

**[DO]** Click **Approve & raise**.

> **SAY** "Approved — and because §8.1 says who and when, that just went into the audit trail."

### 3:25 — Filters and exports (25 s)

**[DO]** Close the drawer. Click the **RFQ** chip, then **All**. Type `PR-26` in search, then clear it.

> **SAY** "The buyer can slice by route, search by PR, item or supplier, and pull the two scored
> exports: decisions.csv in the exact output schema, and preferred.csv as of any date."

**[DO]** Click **decisions.csv** once so the download appears in the corner (optional, 3 s).

### 3:50 — **Live change 1**: a limit is data, not code (50 s)

**[DO]** Top-right role → **Procurement**. Click **Policy (data)**.

> **SAY** "Now the part the brief cares about most. The role switch is there so procurement authority
> is explicit. Every limit, window and rule order in this app is read from a versioned JSON document —
> there is no threshold in the engine."

**[DO]** Click the chip **“Raise the Spot PO limit to 3,00,000”** → **Preview changes**.

> **SAY** "A plain-English amendment, parsed into a structured operation on the document: change the
> Spot PO threshold from two lakh to three lakh. It shows the diff and the ops, and it is a *draft* —
> nothing is active yet."

**[DO]** Click **Approve & activate** (toast: *Policy v5.1 is now active*).

> **SAY** "v5.1 is active, v5.0 is kept and superseded, both dated. No code was edited and nothing was
> redeployed."

### 4:40 — Proof it changed decisions (40 s)

**[DO]** Role → **Buyer**. **Buyer workspace** → **Process sample batch**. Type `PR-26-00001` in search.

> **SAY** "Same batch, same code, new policy version. This line sits in REQ-0143 at ₹2,58,957 — under
> v5.0 it was an RFQ, because it was above two lakh. Under v5.1 it's a Spot PO. Across the batch, Spot
> POs went 60 → 72 and RFQs 39 → 27."

**[DO]** Point at the route cell, then at the header's `policy v5.1`.

### 5:20 — **Live change 2**: a rule kind that did not exist (40 s)

**[DO]** **Policy (data)** → open **Advanced — apply structured ops (no AI needed)** → the example ops
are prefilled → click **Preview these ops**.

> **SAY** "The harder case: a kind of rule that has never existed. For plant CHK1, anything above
> three lakh must go to RFP — a condition on plant *and* value, inserted before rule 5.5. It's data: a
> condition over two fields, not a new branch in the engine. This is also the path an AI-parsed
> amendment produces, so the two are the same mechanism."

**[DO]** Click **Approve & activate** (toast: *Policy v5.2 is now active*).

### 6:00 — Proof again (25 s)

**[DO]** **Buyer workspace** → **Process sample batch** → click the **RFP** chip.

> **SAY** "Seven CHK1 requirements moved from RFQ to RFP — 4 RFP before, 11 now — with zero engine
> changes. That is what 'policy as data' has to mean."

### 6:25 — Contracts and audit (30 s)

**[DO]** **Contracts**: point at a utilisation bar, then the status chips.

> **SAY** "Contracts are first-class, with ceiling, consumed value and utilisation. Contracts signed
> after the register's last update exist only as PDFs — they are entered here and bind from their start
> date at zero consumption. The validity column says active, ends in N days, or expired."

**[DO]** **Audit trail**: filter by an action, expand a row.

> **SAY** "Every action is logged with actor, entity and time: runs, approvals, overrides with their
> written reason, policy drafts, activations."

### 6:55 — `DECISIONS.md` (25 s)

**[DO]** Open `DECISIONS.md` in your editor, scroll to **D-10**, then **D-19**, **D-20**.

> **SAY** "Twenty-two recorded judgment calls for where the policy was silent — the ranking formula and
> its weights (D-10), which policy version a run is judged under (D-19), and how a brand-new rule kind
> is applied without code (D-20). Each one says what I noticed, what I chose, and why."

### 7:20 — Tests and close (15 s)

**[DO]** Switch to a terminal and run it on camera:

```bash
.venv/bin/python -m pytest        # 25 passed
```

> **SAY** "Fourteen worked decisions and three preferred-supplier rankings from the kit are automated
> tests, plus the amendment loop and the export schema. Thanks for watching."

**[DO]** Stop the recording. Do not trim the opening — reviewers start at 0:00.

---

## 3 · Optional 20-second beat (only if you are running under 7:40)

**Override with a reason** — in the drawer, **Override…** → change the route → type
*"single-source approved by plant head, PO history thin"* → **Save override**.

> **SAY** "Overriding requires a written reason, and both the original decision and the reason are kept
> — §8.1."

Skip it if you are already near 8:00; the policy changes matter more than the override.

---

## 4 · The two live changes (copy-paste)

**Change 1 — plain English.** Click the chip, or paste:

```
Raise the Spot PO limit to 3,00,000
```

Expected preview: *Change **Spot PO** threshold from **Rs 200,000** to **Rs 300,000**.* → draft v5.1.

**Change 2 — a new kind of rule.** The advanced panel is already prefilled with exactly this; just
click **Preview these ops**:

```json
[{"op":"add_rule","before":"5.5","rule":{
  "id":"amend-chk1-large-rfp","clause":"amend-1","name":"CHK1 large buys always RFP",
  "when":{"all":[{"field":"requirement.plant","op":"eq","value":"CHK1"},
                 {"field":"requirement.value","op":"gt","value":300000}]},
  "outcome":{"decision":"SOURCING_REQUEST","route":"RFP","supplier_strategy":"suggest_5"}}}]
```

Expected preview: *Add a new rule `amend-chk1-large-rfp` (CHK1 large buys always RFP) -> RFP before
rule 5.5.* → draft v5.2.

**Expected route counts after reprocessing the same batch**

| Policy | Spot PO | RFQ | RFP | Everything else |
|---|---|---|---|---|
| v5.0 | 60 | 39 | 4 | Contract PO 30 · Emergency PO 6 · Capex 10 · New item 2 |
| v5.1 (spot limit ₹3,00,000) | 72 | 27 | 4 | unchanged |
| v5.2 (+ CHK1 rule before 5.5) | 72 | 20 | 11 | unchanged |

**Numbers to have on the tip of your tongue**

- 186 PR lines → 151 requirements; 96 PO-bound requirements → 84 POs; 55 to sourcing.
- PO value ₹1,12,14,692; sourcing value ₹5,12,60,623.
- REQ-0001: Spot PO, ₹1,31,676, basis 3.1(b), S020, PO-0001.
- REQ-0143 (contains PR-26-00001): ₹2,58,957 — RFQ under v5.0, Spot PO under v5.1.
- Tests: 25 passed.

---

## 5 · If something goes wrong on camera

| Symptom | Fix |
|---|---|
| Numbers differ from this script | You are not on v5.0 / not the kit batch → `rm -f api/app.db`, restart, reprocess |
| "Could not derive any changes" | The sentence missed the parser → paste the exact chip text, or use the ops panel |
| Buttons do nothing / "switch role" | Role must be **Procurement** to amend, **Buyer** to approve |
| Spot POs still 60 after approving v5.1 | You approved a draft but reprocessed before it activated — check the version chip, reprocess again |
| Empty table | Click **Process sample batch**; if it errors, `data/` is missing (see `data/README.md`) |
| Banner "No data or policy loaded" | `data/` or `docs/policy-v5.json` missing — see `SUBMISSION.md` §2 |
| A wrong number slips out mid-sentence | Stop, reset, re-record that section. Never talk over a wrong figure |
| You fumble the approval | Reset and retake from 3:50; splice, keep the audio continuous |
| App is slow on the first click | Let the batch finish before talking; do a warm-up run, then reset |

---

## 6 · Export and upload

- QuickTime: **File → Export As → 1080p**. OBS: **File → Remux Recordings** (mkv → mp4).
- Target: 1080p H.264 MP4, audio ~128 kbps, **under 8 minutes**, **under 200 MB**.
- Upload **unlisted** (YouTube) or link-shared (Loom/Drive). Test the link in a private window.
- Paste the link in **three** places, before the freeze: `README.md` → *Demo video*, `SUBMISSION.md` §1,
  and the submission form/email.
- Then run the checklist in `SUBMISSION_CHECKLIST.md` §2 — a link in a doc is not a submitted link.

**The one thing reviewers look for:** a decision changing *because of an amendment made in the UI*, with
the version chip and the route counts moving. If your take does not show that, re-record 3:50–6:00.
