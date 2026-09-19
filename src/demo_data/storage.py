"""Keep every generated artifact inside the agreed repository directory."""

from pathlib import Path


OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "distributor-demo"


def validate_output(path: Path) -> Path:
    """Reject outside paths, parent directories and symlink escapes before writes."""
    resolved = path.resolve()
    root = OUTPUT_ROOT.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"Output must be a new subdirectory of {root}")
    return resolved
