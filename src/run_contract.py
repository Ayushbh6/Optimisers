"""Shared, reproducible contract for a Part 1 pipeline run.

The old pipeline used files in ``artifacts/`` as implicit inputs.  This module
makes the dates, output location and input identity explicit so stages cannot
silently combine results from different runs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from typing import Any


SCHEMA_VERSION = "part1-v2"


@dataclass(frozen=True)
class RunConfig:
    """Dates and paths shared by every Part 1 stage."""

    project_root: Path
    output_dir: Path
    observation_start: str = "2025-06-01"
    initial_learning_end: str = "2026-01-15"
    replay_start: str = "2026-01-16"
    observation_end: str = "2026-04-24"
    lead_time_days: int = 10
    service_level: float = 0.95
    holding_rate: float = 0.20
    min_order_quantity: int = 5
    return_restock_lag_days: int = 0
    forecast_method: str = "croston"
    alpha: float = 0.1
    beta: float = 0.1
    laplace_prior: float = 1e-4
    minimum_exposure_days: int = 7
    batch_order_cost: float = 50.0
    line_order_cost: float = 2.0
    stocking_threshold: float = 0.004
    startup_days: int = 15
    annual_days: int = 365
    sensitivity_lead_times: tuple = (5, 10, 15)
    sensitivity_service_levels: tuple = (0.90, 0.95, 0.98)
    sensitivity_holding_rates: tuple = (0.15, 0.20, 0.25)
    schema_version: str = SCHEMA_VERSION

    @property
    def raw_dir(self) -> Path:
        return self.project_root / "data" / "raw"

    @property
    def sales_path(self) -> Path:
        return self.raw_dir / "retail_sales_ml_apl.csv"

    @property
    def inventory_path(self) -> Path:
        return self.raw_dir / "retail_inventory_ml_apl.csv"

    def artifact_path(self, name: str) -> Path:
        return self.output_dir / name

    def validate(self) -> None:
        ordered = [
            self.observation_start,
            self.initial_learning_end,
            self.replay_start,
            self.observation_end,
        ]
        parsed = [date.fromisoformat(value) for value in ordered]
        if not (parsed[0] <= parsed[1] < parsed[2] <= parsed[3]):
            raise ValueError("Run dates must be observation_start <= learning_end < replay_start <= observation_end")
        if parsed[2] != parsed[1] + timedelta(days=1):
            raise ValueError("Replay must start immediately after initial learning")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Mismatched run schema")
        if self.forecast_method not in {"croston", "tsb"}:
            raise ValueError("Unsupported forecast method")
        if not (0 < self.alpha <= 1 and 0 < self.beta <= 1 and 0 < self.service_level < 1):
            raise ValueError("Invalid smoothing or service assumption")
        if self.holding_rate <= 0 or self.lead_time_days < 1 or self.min_order_quantity < 1:
            raise ValueError("Invalid holding rate, lead time or minimum quantity")
        if self.return_restock_lag_days != 0:
            raise ValueError("Part 1 supports only same-day historical return restocking")


def default_run_config(project_root: Path | None = None, output_dir: Path | None = None) -> RunConfig:
    """Create the default contract without writing to disk."""
    root = project_root or Path(__file__).resolve().parent.parent
    return RunConfig(project_root=root, output_dir=output_dir or root / "artifacts" / "part1")


def sha256_file(path: Path) -> str:
    """Return a content hash without loading a raw input into memory at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision(project_root: Path) -> str | None:
    """Return the checked-out revision when Git is available."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_identity(project_root: Path) -> dict[str, str]:
    """Hash the implementation files, including untracked files in the run.

    A Git ``HEAD`` is useful context but does not describe local edits.  The
    source hashes make a manifest honest while a repair is still uncommitted.
    """
    try:
        names = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=project_root, text=True, stderr=subprocess.DEVNULL,
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        names = []
    files: dict[str, str] = {}
    for name in sorted(set(names)):
        path = project_root / name
        if path.is_file() and (
            name.startswith("src/") or name.startswith("tests/") or name == "requirements.txt"
            or name in {"CURRENT_STATUS.md", "PLAN_phase_2.md", "docs/OPTIMISER_LOGIC.md", "docs/REPO_RULES.md"}
        ):
            files[name] = sha256_file(path)
    return files


def config_payload(config: RunConfig) -> dict[str, Any]:
    """Convert paths to strings for a stable manifest."""
    payload = asdict(config)
    return {key: str(value) if isinstance(value, Path) else value for key, value in payload.items()}


def write_manifest(config: RunConfig, artifacts: dict[str, Path], limitations: list[str]) -> Path:
    """Write the single auditable record of a completed Part 1 run."""
    config.validate()
    missing = [str(path) for path in (config.sales_path, config.inventory_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing raw inputs: {missing}")
    expected = {
        "pyarrow": "25.0.1",
        "pytest": "9.1.1",
    }
    installed = {
        package: importlib.metadata.version(package)
        for package in ("numpy", "pandas", "scipy", "pyarrow", "pytest")
        if _installed(package)
    }
    mismatched = {name: {"expected": version, "installed": installed.get(name)}
                  for name, version in expected.items() if installed.get(name) != version}
    if mismatched:
        raise RuntimeError(f"Pinned run dependencies are unavailable: {mismatched}")
    stage_dependencies = {
        "daily_onhand.parquet": ["raw_inputs"],
        "demand.parquet": ["daily_onhand.parquet"],
        "forecast.parquet": ["demand.parquet"],
        "forecast_benchmark_detail.parquet": ["demand.parquet"],
        "forecast_benchmark_summary.parquet": ["forecast_benchmark_detail.parquet"],
        "policy.parquet": ["forecast.parquet", "daily_onhand.parquet"],
        "replay_ledger.parquet": ["daily_onhand.parquet", "demand.parquet", "policy.parquet"],
        "replay_breakdown.parquet": ["replay_ledger.parquet"],
        "excluded_purchases.parquet": ["daily_onhand.parquet"],
        "part1_report.md": ["matched_comparisons.parquet", "replay_breakdown.parquet", "forecast_benchmark_summary.parquet"],
        "matched_comparisons.parquet": ["daily_onhand.parquet", "replay_ledger.parquet"],
        "pending_orders.parquet": ["replay_ledger.parquet"],
        "sensitivity.parquet": ["daily_onhand.parquet", "demand.parquet"],
        "acceptance_checks.json": ["daily_onhand.parquet", "replay_ledger.parquet", "replay_breakdown.parquet"],
    }
    payload = {
        "schema_version": config.schema_version,
        "config": config_payload(config),
        "git_revision": git_revision(config.project_root),
        "implementation_root": str(Path(__file__).resolve().parent.parent),
        "source_identity": source_identity(Path(__file__).resolve().parent.parent),
        "raw_inputs": {
            str(config.sales_path): sha256_file(config.sales_path),
            str(config.inventory_path): sha256_file(config.inventory_path),
        },
        "dependencies": installed,
        "stage_dependencies": {name: stage_dependencies.get(name, []) for name in artifacts},
        "artifacts": {name: {"path": str(path), "sha256": sha256_file(path)} for name, path in artifacts.items()},
        "limitations": limitations,
        "coverage": json.loads(config.artifact_path("acceptance_checks.json").read_text()) if config.artifact_path("acceptance_checks.json").exists() else {},
    }
    path = config.artifact_path("run_manifest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
    return path


def _installed(package: str) -> bool:
    """Return whether a package can be versioned in this environment."""
    try:
        importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True
