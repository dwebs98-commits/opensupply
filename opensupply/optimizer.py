"""Small, explainable transportation-network optimizer."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

REQUIRED_FACILITY_COLUMNS = {"facility", "capacity_units", "fixed_annual_cost", "open"}
REQUIRED_DEMAND_COLUMNS = {"customer", "annual_demand_units"}
REQUIRED_LANE_COLUMNS = {"facility", "customer", "cost_per_unit"}

@dataclass
class OptimizationResult:
    shipments: pd.DataFrame
    facility_summary: pd.DataFrame
    kpis: dict[str, float]
    unmet_demand: pd.DataFrame

def _validate(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(sorted(missing))}")

def optimize_network(facilities: pd.DataFrame, demand: pd.DataFrame, lanes: pd.DataFrame) -> OptimizationResult:
    """Allocate demand to the least-cost open facility with capacity."""
    _validate(facilities, REQUIRED_FACILITY_COLUMNS, "Facilities")
    _validate(demand, REQUIRED_DEMAND_COLUMNS, "Demand")
    _validate(lanes, REQUIRED_LANE_COLUMNS, "Lanes")
    if (demand["annual_demand_units"] < 0).any() or (facilities["capacity_units"] < 0).any():
        raise ValueError("Demand and capacity must be non-negative.")
    is_open = facilities["open"].astype(str).str.lower().isin(["true", "1", "yes"])
    open_facilities = facilities[is_open].copy()
    capacity = open_facilities.set_index("facility")["capacity_units"].astype(float).to_dict()
    eligible_lanes = lanes[lanes["facility"].isin(capacity)].copy()
    eligible_lanes["cost_per_unit"] = eligible_lanes["cost_per_unit"].astype(float)
    allocations, unmet = [], []
    for row in demand.sort_values("annual_demand_units", ascending=False).itertuples(index=False):
        customer, remaining = row.customer, float(row.annual_demand_units)
        for lane in eligible_lanes[eligible_lanes["customer"] == customer].sort_values("cost_per_unit").itertuples(index=False):
            quantity = min(remaining, capacity[lane.facility])
            if quantity > 0:
                allocations.append({"facility": lane.facility, "customer": customer, "annual_units": quantity, "cost_per_unit": lane.cost_per_unit, "annual_transport_cost": quantity * lane.cost_per_unit})
                capacity[lane.facility] -= quantity
                remaining -= quantity
            if remaining <= 1e-9:
                break
        if remaining > 1e-9:
            unmet.append({"customer": customer, "unmet_units": remaining})
    shipments = pd.DataFrame(allocations, columns=["facility", "customer", "annual_units", "cost_per_unit", "annual_transport_cost"])
    summary = open_facilities[["facility", "capacity_units", "fixed_annual_cost"]].copy()
    used = shipments.groupby("facility")["annual_units"].sum() if not shipments.empty else pd.Series(dtype=float)
    transport = shipments.groupby("facility")["annual_transport_cost"].sum() if not shipments.empty else pd.Series(dtype=float)
    summary["assigned_units"] = summary["facility"].map(used).fillna(0.0)
    summary["remaining_capacity"] = summary["capacity_units"] - summary["assigned_units"]
    summary["utilization_pct"] = (100 * summary["assigned_units"] / summary["capacity_units"].replace(0, pd.NA)).fillna(0.0)
    summary["transport_cost"] = summary["facility"].map(transport).fillna(0.0)
    unmet_frame = pd.DataFrame(unmet, columns=["customer", "unmet_units"])
    transport_cost = float(shipments["annual_transport_cost"].sum()) if not shipments.empty else 0.0
    fixed_cost = float(open_facilities["fixed_annual_cost"].astype(float).sum())
    kpis = {"total_demand_units": float(demand["annual_demand_units"].sum()), "served_units": float(shipments["annual_units"].sum()) if not shipments.empty else 0.0, "unmet_units": float(unmet_frame["unmet_units"].sum()) if not unmet_frame.empty else 0.0, "transport_cost": transport_cost, "fixed_cost": fixed_cost, "total_cost": transport_cost + fixed_cost}
    return OptimizationResult(shipments, summary, kpis, unmet_frame)

def to_excel(result: OptimizationResult) -> bytes:
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result.shipments.to_excel(writer, sheet_name="Shipments", index=False)
        result.facility_summary.to_excel(writer, sheet_name="Facilities", index=False)
        pd.DataFrame([result.kpis]).to_excel(writer, sheet_name="Summary", index=False)
        result.unmet_demand.to_excel(writer, sheet_name="Unmet demand", index=False)
    return buffer.getvalue()
