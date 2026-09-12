"""Compatibility entrypoint for controlled FlyEM male CNS graph preparation.

The public data remain attributed to FlyEM (CC-BY). Pure construction now lives
in flytrap.data.graph; the CLI records source checksums and anatomical metadata.
"""

from flytrap.data.graph import MIN_SYN, MV_PER_SYNAPSE, SIGN, build_graph  # noqa: F401


def main():
    import sys
    from flytrap.cli import main as cli_main

    return cli_main(["data-build", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
