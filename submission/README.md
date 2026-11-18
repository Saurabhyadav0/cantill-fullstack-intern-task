# submission/

Blind-test outputs go here on Thu 19 Nov, committed **before 12:00 noon IST**.

| File | Contents |
|---|---|
| `<name>__run1.csv` | the new batch processed under policy **v5.0** |
| `<name>__run2.csv` | the same batch after approving the amendment **through the app** |
| `<name>__preferred.csv` | preferred-supplier lists as of the given date |

`<name>` = your name, exactly as the brief asks (e.g. `saurabh__run1.csv`).

## How to produce them

1. Buyer workspace → **Upload batch CSV** → confirm the policy version chip → **decisions.csv** →
   save as `<name>__run1.csv`.
2. Role **Procurement** → Policy (data) → paste/describe the amendment → **Preview** →
   **Approve & activate** (use the *Advanced — structured ops* panel if the text parser misses it).
3. Role **Buyer** → reprocess the **same** batch → **decisions.csv** → `<name>__run2.csv`.
4. Set the date box next to **preferred.csv** to the date they give → download → `<name>__preferred.csv`.
5. Run the checks in `SUBMISSION.md` §4 (run1 vs run2 differ; no Blocked/Inactive supplier), then
   `git add submission/ && git commit && git push`.

No code changes after the 10:00 freeze — these files are produced entirely through the UI.
