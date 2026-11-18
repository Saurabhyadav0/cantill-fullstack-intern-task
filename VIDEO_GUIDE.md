# VIDEO_GUIDE — record the walkthrough in ~20 minutes

Round 2 asks for a short walkthrough of the app plus `DECISIONS.md`, **and a change made live**.
This guide gives you a 7–8 minute shot list, the exact words to say, the exact clicks, and the
two live policy changes to demo. One rehearsal, then record.

> Numbers quoted below come from the shipped sample batch (186 PR lines → 151 requirements) and
> are the ones you should see on screen. If yours differ, you changed the data — not the script.

---

## 0 · Before you hit record (5 minutes)

**Start the app**

```bash
cd ~/Desktop/Cantill-FullStack-Intern-Task
. .venv/bin/activate
uvicorn api.main:app --port 8000
# open http://localhost:8000
```

If port 8000 is busy, find and stop the old server first (never kill by name pattern):

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN     # note the PID
kill <PID>
```

**Clean slate for a repeatable take** (optional but recommended for a second take):

```bash
rm -f api/app.db        # deletes versions/audit/runs; restart uvicorn → policy v5.0 reseeded
```

**Recording setup**

| Thing | Do this |
|---|---|
| Recorder | macOS `Cmd+Shift+5` → *Record Selected Portion* (pick a 16:9 area), or OBS at 1920×1080 |
| Audio | Built-in mic is fine if the room is quiet; test 10 seconds before the real take |
| Browser | `Cmd +` to ~110% zoom, hide the bookmarks bar (`Cmd+Shift+B`), one tab only |
| Window | 1440×900 or larger — below ~860px the sidebar becomes a top bar |
| Noise | Do Not Disturb on; Slack/WhatsApp closed; phone silent |
| Cursor | Move slowly and pause on the thing you are describing |

**One rehearsal** end-to-end without recording. Then reset the DB and record.

---

## 1 · Shot list (target 7:30)

| Time | Tab / screen | You do | You say (the point) |
|---|---|---|---|
| 0:00 | Chat intake | — | What the app is: chat intake, policy-as-data engine, buyer workspace |
| 0:30 | Chat intake | Click the first suggestion → Create PR | Item matched from free text, slots filled, nothing invented |
| 1:10 | Chat intake | Type a vague item, then an unknown one | It asks / flags NEW instead of guessing |
| 1:30 | Buyer workspace | Process sample batch | 186 lines → 151 requirements; 96 PO, 55 sourcing |
| 2:10 | Buyer workspace | Open REQ-0001, read the drawer | Every decision carries clause + contract/PO + policy version |
| 3:00 | Buyer workspace | Show ranking panel, approve one | "Why is this supplier first?" — weights live in the policy |
| 3:30 | Buyer workspace | Show route filters + exports | Decisions are actionable and exportable in the scored schema |
| 4:00 | Policy (data), role = Procurement | Spot limit → 3,00,000 → Preview → Approve | A limit change is a new policy version, not a deploy |
| 5:00 | Buyer workspace | Reprocess, search PR-26-00001 | Same batch, same code — decision flipped RFQ → SPOT_PO |
| 5:40 | Policy (data) | Advanced → Preview these ops → Approve | A brand-new rule kind (plant-specific) also as data |
| 6:20 | Buyer workspace | Reprocess, filter RFP | 7 Chikali/CHK1 requirements moved RFQ → RFP |
| 6:50 | Contracts, Audit trail | Hover utilisation, show audit rows | Ceilings and who-did-what are first-class |
| 7:15 | Editor: DECISIONS.md | Scroll D-10, D-19, D-20 | Judgment calls and their reasoning |
| 7:30 | Terminal | `pytest` green | 14 worked decisions + 3 rankings reproduced |

---

## 2 · Script (say it roughly like this)

### 0:00 — Intro (30 s)
> "This is Corvo's procurement app: employees raise purchase requests by chatting, and the system
> decides whether to place a purchase order or raise a sourcing request — by following the
> procurement policy stored as data. The engine is pure Python; this is a FastAPI service serving
> a small React UI. Everything you see is driven by the active policy version in the top bar."

### 0:30 — Chat intake (40 s)
Click **Chat intake** → click the chip **“need 200 nitrile gloves for Chakan by next Friday”**.

> "Free text. It matched the item to ITM-1048 nitrile gloves — not by an item code, by description —
> filled quantity 200, plant CHK1, and the need-by date. The right panel is the PR draft; each tick
> is a required field. Nothing is invented: if it can't match, it says so."

Click **Create PR** → note *“Created PR-NEW-00001”*.

### 1:10 — It asks instead of guessing (20 s)
Type `2 ball bearings for Pune by 2026-12-01` and press Enter.

> "Two items are close on score, so it shows candidates and asks instead of picking one." (Click the
> right one.)
> "And an item that doesn't exist…" — type `flux capacitor 2 units for Pune` → **it flags it as NEW
> and sends it to sourcing** rather than inventing a code.

### 1:30 — Buyer workspace (40 s)
Click **Buyer workspace** → **Process sample batch**.

> "186 PR lines become 151 requirements by clubbing — same item, same plant, inside the policy's
> 14-day and ±7-day windows. 96 end in a PO, 55 in sourcing, and those 96 PO requirements
> consolidate into 84 POs."

### 2:10 — Why (50 s)
Click **REQ-0001**.

> "Each requirement explains itself: Spot PO, clause 5.4, value ₹1,31,676 valued at the most recent
> PO price under 3.1(b), supplier S020 at the reference price, PO-0001 after consolidation. The
> policy version is recorded on the decision, so an audit can tell which rules applied."

### 3:00 — Explainable ranking (30 s)
Scroll the drawer to **Preferred suppliers**.

> "This is §6: every Active supplier that sold us the item in 548 days or held a contract. The
> score is not a black box — 30% frequency, 25% recency, 20% contract, 15% on-time, 10% quality —
> and those weights are themselves in the policy document. The one used on this decision is marked."

Click **Approve & raise** → status becomes *approved*.

### 3:30 — Acting on it (30 s)
Close the drawer. Click a route chip (**RFQ**), then **All**.

> "Filters by route, search by PR number or supplier, and the two scored exports: decisions.csv in
> the exact output schema, and preferred.csv as of any date."

### 4:00 — Policy as data (60 s)
Top-right role → **Procurement**. Click **Policy (data)** → click the chip
**“Raise the Spot PO limit to 3,00,000”** → **Preview changes**.

> "The amendment was parsed into an operation over the policy document: change the Spot PO
> threshold from 200,000 to 300,000. Nothing is active yet."

Click **Approve & activate** → *Policy v5.1 is now active*.

> "Version 5.0 is kept, 5.1 is active, both dated. No code was touched, nothing was redeployed."

### 5:00 — Prove it changed decisions (40 s)
**Buyer workspace** → **Process sample batch** → in the search box type `PR-26-00001`.

> "Same batch, same code, new policy version. This requirement was RFQ before — now it's a Spot PO
> at ₹2,58,957, because the limit moved. Spot PO count 60 → 72, RFQ 39 → 27."

### 5:40 — A brand-new kind of rule (45 s)
**Policy (data)** → open **Advanced — apply structured ops (no AI needed)** → **Preview these ops**.

> "This is the harder case the brief cares about: a rule kind that didn't exist before — plant
> specific. For plant CHK1, anything above ₹3,00,000 must go to RFP. It's data: a condition over
> `requirement.plant` and `requirement.value`, inserted before rule 5.5."

Click **Approve & activate** → v5.2.

### 6:20 — Prove that too (25 s)
**Buyer workspace** → **Process sample batch** → filter **RFP**.

> "Seven CHK1 requirements moved from RFQ to RFP, with no engine change. That's the whole point of
> policy-as-data."

### 6:50 — Contracts + audit (30 s)
**Contracts** → point at utilisation bars.

> "Contracts are first-class, including PDF-only ones signed after the register update — they start
> at zero consumption and bind from their start date."

**Audit trail**.

> "Every action is logged with actor and time: processing runs, approvals, overrides with their
> written reason, policy drafts and activations."

### 7:15 — DECISIONS.md (20 s)
Open `DECISIONS.md` in your editor.

> "Twenty-one judgment calls where the policy was silent — the ranking formula (D-10), which policy
> version a run uses (D-19), and how new rule kinds work without code (D-20)."

### 7:30 — Close (15 s)
In a terminal:

```bash
.venv/bin/python -m pytest      # 25 passed
```

> "14 worked decisions and 3 preferred-supplier rankings reproduced as automated tests. Thanks."

Stop recording.

---

## 3 · The two live changes (copy-paste)

**Change 1 — plain English.** Paste in the amendment box:

```
Raise the Spot PO limit to 3,00,000
```

Expected preview: *Change **Spot PO** threshold from **Rs 200000** to **Rs 300000**. → v5.1*

**Change 2 — new rule kind.** The advanced panel is prefilled; just click **Preview these ops**:

```json
[{"op":"add_rule","before":"5.5","rule":{
  "id":"amend-chk1-large-rfp","clause":"amend-1","name":"CHK1 large buys always RFP",
  "when":{"all":[{"field":"requirement.plant","op":"eq","value":"CHK1"},
                 {"field":"requirement.value","op":"gt","value":300000}]},
  "outcome":{"decision":"SOURCING_REQUEST","route":"RFP","supplier_strategy":"suggest_5"}}}]
```

Expected preview: *Add a new rule `amend-chk1-large-rfp` … -> RFP before rule 5.5.* → v5.2

**Expected totals after reprocessing the sample batch**

| Policy | Spot PO | RFQ | RFP | Everything else |
|---|---|---|---|---|
| v5.0 | 60 | 39 | 4 | Contract 30 · Emergency 6 · Capex 10 · New 2 |
| v5.1 (spot limit) | 72 | 27 | 4 | unchanged |
| v5.2 (+ CHK1 rule) | 72 | 20 | 11 | unchanged |

---

## 4 · If something goes wrong on camera

| Symptom | Fix |
|---|---|
| Preview says "could not derive any changes" | The sentence didn't match the parser — use the advanced ops panel instead |
| Buttons do nothing / "switch role" | Set the top-right role to **Procurement** before amending, **Buyer** before approving |
| Table is empty | Click **Process sample batch** (data must exist in `data/` — see `data/README.md`) |
| Banner "No data or policy loaded" | `data/` or `docs/policy-v5.json` missing; see `SUBMISSION.md` §2 |
| Wrong/odd decisions after experimenting | `rm -f api/app.db`, restart uvicorn, reprocess |

---

## 5 · Export & upload

- QuickTime: **File → Export As → 1080p**. OBS: *File → Remux Recordings* (mkv → mp4).
- Target: 1080p, H.264 MP4, audio 128 kbps, under ~8 minutes, file < 200 MB.
- Upload **unlisted** to YouTube, or Loom/Drive with link-sharing on.
- Put the link in three places: `README.md` → **Demo video**, `SUBMISSION.md` §1, and the submission form/email.

**Final check before you upload:** the video shows a decision changing because of an amendment made
in the UI — that is the single thing reviewers look for. If your take doesn't show it, re-record
just section 4:00–6:20 and splice.
