"""Thin stage entrypoint into the shared reproducible Part 1 build."""
from src.build_part1 import main, run_part1
from src.run_contract import RunConfig


def run_pipeline(config: RunConfig):
    """Build from raw records with the shared run contract, never legacy artifacts."""
    return run_part1(config)


if __name__ == '__main__':
    raise SystemExit(main())
