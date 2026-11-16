import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.loaders import load_master_data, load_policy, load_pr_lines   # noqa: E402
from engine.core import process_batch                                     # noqa: E402

DATA = os.path.join(ROOT, "data")
POLICY = os.path.join(ROOT, "docs", "policy-v5.json")
BATCH = os.path.join(DATA, "pr_batches", "sample_pr_batch.csv")

_missing = not (os.path.exists(BATCH) and os.path.exists(POLICY))
requires_data = pytest.mark.skipif(_missing, reason="kit data not present (see data/README.md)")


@pytest.fixture(scope="session")
def md():
    return load_master_data(DATA)


@pytest.fixture(scope="session")
def policy():
    return load_policy(POLICY)


@pytest.fixture(scope="session")
def result(md, policy):
    lines = load_pr_lines(BATCH)
    rows, reqs = process_batch(md, policy, lines)
    by_line = {(r.pr_no, int(r.pr_line)): r for r in rows}
    return {"rows": rows, "reqs": reqs, "by_line": by_line}
