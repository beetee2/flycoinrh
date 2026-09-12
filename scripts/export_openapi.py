"""Export the currently implemented HTTP surface, with a deterministic drift check."""
import argparse
import json
from pathlib import Path

from flytrap.api import create_app

OUTPUT = Path(__file__).resolve().parents[1] / "docs/implementation/contracts/openapi.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(create_app().openapi(), sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != expected:
            print("OpenAPI snapshot is stale; run make generate")
            return 1
        print("OpenAPI snapshot matches implemented health/config routes")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
