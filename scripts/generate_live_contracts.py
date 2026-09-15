"""Generate/check live JSON schemas and the shared synthetic validation corpus."""
import argparse
import json
from pathlib import Path

from flytrap.live.contracts import CONTRACTS
from scripts.live_contract_examples import corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "web/src/live/generated"
    outputs = {"schemas.json": {name: cls.model_json_schema() for name, cls in CONTRACTS.items()},
               "examples.json": corpus()}
    for name, value in outputs.items():
        expected = json.dumps(value, indent=2, allow_nan=False) + "\n"
        target = root / name
        if args.check:
            if not target.exists() or target.read_text() != expected:
                raise SystemExit(f"Stale live contract: {target}. Run make generate-live.")
        else:
            root.mkdir(parents=True, exist_ok=True)
            target.write_text(expected)


if __name__ == "__main__":
    main()
