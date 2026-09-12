"""Generate or check the P00 result schema consumed by browser AJV validation."""
import argparse
import json
from pathlib import Path

from flytrap.lab.contracts import LabResult


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path('web/src/generated/lab-result.schema.json')
    expected = json.dumps(LabResult.model_json_schema(), indent=2) + '\n'
    if args.check:
        if target.read_text() != expected:
            raise SystemExit('P00 response schema is stale')
    else:
        target.write_text(expected)


if __name__ == '__main__':
    main()
