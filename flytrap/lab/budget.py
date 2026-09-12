"""Append-only attempted-call ledger; caller holds the exclusive model lock."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .contracts import CALL_CAP


class BudgetExceeded(RuntimeError):
    pass


class CallBudget:
    def __init__(self, path: Path):
        self.path = path

    @property
    def attempted(self):
        if not self.path.exists():
            return 0
        rows = self.path.read_text().splitlines()
        if len(rows) > CALL_CAP:
            raise ValueError("call ledger exceeds cap")
        for number, line in enumerate(rows, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or type(row.get("attempt")) is not int or row["attempt"] != number:
                raise ValueError("invalid call ledger; fail closed")
        return len(rows)

    def record_attempt(self, *, result_id, seed, side):
        count = self.attempted
        if count >= CALL_CAP:
            raise BudgetExceeded("P00 attempted-call cap reached")
        row = dict(attempt=count + 1, result_id=result_id, seed=seed, side=side,
                   started_at=datetime.now(timezone.utc).isoformat())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return count + 1
