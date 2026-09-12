"""Export deterministic JSON Schemas; --check fails on stale/missing output."""

import argparse
import json
from pathlib import Path

from flytrap.contracts import CONTRACTS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web/src/generated/schemas.json"


def generate() -> str:
    schemas = {}
    for name, model in sorted(CONTRACTS.items()):
        schema = model.model_json_schema(mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://flytrap.invalid/contracts/v1/{name}"
        schemas[name] = schema
    return json.dumps(schemas, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != expected:
            print(f"Stale contract schema: {OUTPUT}")
            return 1
        print(f"Verified {len(CONTRACTS)} generated contract schemas")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected)
    print(f"Generated {len(CONTRACTS)} contract schemas: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
