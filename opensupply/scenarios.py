"""Simple annual-cost and payback comparison for logistics scenarios."""
from __future__ import annotations
import pandas as pd

REQUIRED = {"scenario", "purpose", "outbound_freight", "inbound_freight", "port_management", "facility_rent", "facility_operating", "one_time_implementation", "total_pe", "total_weight_lbs", "service_1_day", "service_2_day", "service_3_day"}

def compare_scenarios(scenarios: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED - set(scenarios.columns)
    if missing:
        raise ValueError(f"Scenarios are missing required columns: {', '.join(sorted(missing))}")
    result = scenarios.copy()
    components = ["outbound_freight", "inbound_freight", "port_management", "facility_rent", "facility_operating"]
    result["annual_cost"] = result[components].sum(axis=1)
    baseline = float(result.iloc[0]["annual_cost"])
    result["annual_savings"] = baseline - result["annual_cost"]
    result["payback_years"] = result.apply(lambda row: row.one_time_implementation / row.annual_savings if row.annual_savings > 0 and row.one_time_implementation > 0 else pd.NA, axis=1)
    result["five_year_net_savings"] = result["annual_savings"] * 5 - result["one_time_implementation"]
    result["cost_per_pe"] = result["annual_cost"] / result["total_pe"].replace(0, pd.NA)
    result["cost_per_lb"] = result["annual_cost"] / result["total_weight_lbs"].replace(0, pd.NA)
    return result
