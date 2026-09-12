"""Small raw-to-report checks for the repaired Part 1 runner."""

from pathlib import Path

import pandas as pd

from src.build_part1 import _replay_breakdown, run_part1
from src.run_contract import RunConfig


def _raw_fixture(root: Path) -> None:
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    common = {
        "Stock Status": "Full Price", "Supplier": "vendor", "Product No": "P1",
        "Product Description": "test", "Product Division": "D", "Product Category": "C",
        "Product Subcategory": "SC", "Product Segment": "SG", "Store": "S1",
        "Store Type": "Retail", "Sales Channel": "A", "Stocks Selling Amount": 20.0,
        "Cost of Stocks": 10.0, "Stock Unit Selling Price": 2.0, "Stock Unit Cost Price": 1.0,
    }
    pd.DataFrame([
        {**common, "Start Date": "2025-06-01", "End Date": "2026-01-14", "Qty on hand": 10},
        {**common, "Start Date": "2026-01-15", "End Date": "9999-12-31", "Qty on hand": 3},
    ]).to_csv(raw / "retail_inventory_ml_apl.csv", index=False)
    sale = {"Sales Type": "Full Price", "Is Return": 0, "Reason of Return": None,
            "Supplier": "vendor", "Product No": "P1", "Product Description": "test",
            "Product Division": "D", "Product Category": "C", "Product Subcategory": "SC",
            "Product Segment": "SG", "Store": "S1", "Sales Channel": "A", "Qty Sold": 1,
            "Sales Amount": 2.0, "Cogs": 1.0, "Number of Transactions": 1}
    pd.DataFrame([{**sale, "Transaction Date": day} for day in ("2025-06-02", "2026-01-16")]).to_csv(
        raw / "retail_sales_ml_apl.csv", index=False
    )


def test_part1_runner_uses_raw_inputs_and_fresh_output(tmp_path):
    _raw_fixture(tmp_path)
    # A malformed legacy artifact must not be read as a stage input.
    legacy = tmp_path / "artifacts"
    legacy.mkdir()
    (legacy / "demand.parquet").write_text("legacy sentinel", encoding="utf-8")
    output = tmp_path / "run"
    result = run_part1(RunConfig(project_root=tmp_path, output_dir=output))
    expected = {"daily_onhand.parquet", "demand.parquet", "forecast.parquet",
                "policy.parquet", "replay_ledger.parquet", "part1_report.md"}
    assert expected <= {path.name for path in result.values()}
    assert (output / "run_manifest.json").exists()
    assert "Historical ordering cost" in (output / "part1_report.md").read_text()

    forecast = pd.read_parquet(output / "forecast.parquet")
    policy = pd.read_parquet(output / "policy.parquet")
    benchmarks = pd.read_parquet(output / "forecast_benchmark_summary.parquet")
    assert {"information_cutoff", "forecast_start_date", "forecast_unit", "forecast_status"} <= set(forecast)
    assert {"policy_status", "no_order_reason", "unit_cost_as_of", "forecast_available"} <= set(policy)
    assert set(benchmarks["target"]) == {"observed_purchases", "estimated_demand"}
    assert (policy["no_order_reason"].notna()).all()


def test_breakdown_sums_each_product_store_ending_stock_before_grouping():
    ledger = pd.DataFrame({
        "Product Division": ["D", "D", "D", "D"],
        "Store": ["S", "S", "S", "S"],
        "Product No": ["P1", "P1", "P2", "P2"],
        "date": pd.to_datetime(["2026-01-16", "2026-01-17", "2026-01-16", "2026-01-17"]),
        "eligible": [True, True, True, True],
        "recorded_gross_purchases_units": [1, 1, 2, 2],
        "fulfilled_purchases_units": [1, 1, 2, 2],
        "unfulfilled_purchases_units": [0, 0, 0, 0],
        "order_qty_units": [0, 0, 0, 0],
        "closing_on_hand_units": [9, 7, 6, 4],
    })
    result = _replay_breakdown(ledger).iloc[0]
    assert result.ending_stock_units == 11


def test_sensitivity_writes_all_27_independent_settings_without_savings_claim(tmp_path):
    _raw_fixture(tmp_path)
    output = tmp_path / "sensitivity-run"
    run_part1(RunConfig(project_root=tmp_path, output_dir=output), run_sensitivity=True)
    settings = pd.read_parquet(output / "sensitivity.parquet")
    assert len(settings) == 27
    assert settings[["lead_time_days", "target_service_level", "holding_rate"]].drop_duplicates().shape[0] == 27
    assert settings["historical_ordering_cost_eur"].isna().all()
    assert settings["total_cost_savings_eur"].isna().all()
