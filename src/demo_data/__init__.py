"""Synthetic packaged-food distributor data for the client demonstration."""

from .audit import audit_scenario
from .config import DemoConfig, default_config
from .generator import generate_scenario
from .snapshot import export_csv, snapshot

__all__ = [
    "DemoConfig",
    "audit_scenario",
    "default_config",
    "export_csv",
    "generate_scenario",
    "snapshot",
]
