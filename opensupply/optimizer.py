"""Small, explainable transportation-network optimizer."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

REQUIRED_FACILITY_COLUMNS = {"facility", "capacity_units", "fixed_annual_cost", "open"}
REQUIRED_DEMAND_COLUMNS = {"customer", "annual_demand_units"}
REQUIRED_LANE_COLUMNS = {"facility", "customer", "cost_per_unit"}
REQUIRED_PORT_COLUMNS = {"port", "capacity_units", "fixed_annual_cost", "open"}
REQUIRED_INBOUND_LANE_COLUMNS = {"port", "facility", "cost_per_unit"}

@dataclass
class OptimizationResult:
    shipments: pd.DataFrame
    facility_summary: pd.DataFrame
    kpis: dict[str, float]
    unmet_demand: pd.DataFrame
    inbound_shipments: pd.DataFrame
    port_summary: pd.DataFrame
    unmet_inbound: pd.DataFrame

def _validate(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(sorted(missing))}")

def _open(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["open"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()

def _allocate_inbound(facilities: pd.DataFrame, ports: pd.DataFrame, lanes: pd.DataFrame):
    open_ports = _open(ports)
    port_capacity = open_ports.set_index("port")["capacity_units"].astype(float).to_dict()
    lanes = lanes[lanes["port"].isin(port_capacity)].copy()
    lanes["cost_per_unit"] = lanes["cost_per_unit"].astype(float)
    allocations, unmet = [], []
    for facility in facilities.sort_values("assigned_units", ascending=False).itertuples(index=False):
        remaining = float(facility.assigned_units)
        for lane in lanes[lanes["facility"] == facility.facility].sort_values("cost_per_unit").itertuples(index=False):
            quantity = min(remaining, port_capacity[lane.port])
            if quantity:
                allocations.append({"port": lane.port, "facility": facility.facility, "annual_units": quantity, "cost_per_unit": lane.cost_per_unit, "annual_inbound_cost": quantity * lane.cost_per_unit})
                port_capacity[lane.port] -= quantity
                remaining -= quantity
            if remaining <= 1e-9:
                break
        if remaining > 1e-9:
            unmet.append({"facility": facility.facility, "unmet_inbound_units": remaining})
    inbound = pd.DataFrame(allocations, columns=["port", "facility", "annual_units", "cost_per_unit", "annual_inbound_cost"])
    summary = open_ports[["port", "capacity_units", "fixed_annual_cost"]].copy()
    used = inbound.groupby("port")["annual_units"].sum() if not inbound.empty else pd.Series(dtype=float)
    cost = inbound.groupby("port")["annual_inbound_cost"].sum() if not inbound.empty else pd.Series(dtype=float)
    summary["assigned_units"] = summary["port"].map(used).fillna(0.0)
    summary["remaining_capacity"] = summary["capacity_units"] - summary["assigned_units"]
    summary["utilization_pct"] = (100 * summary["assigned_units"] / summary["capacity_units"].replace(0, pd.NA)).fillna(0.0)
    summary["inbound_transport_cost"] = summary["port"].map(cost).fillna(0.0)
    return inbound, summary, pd.DataFrame(unmet, columns=["facility", "unmet_inbound_units"])

def optimize_network(facilities: pd.DataFrame, demand: pd.DataFrame, lanes: pd.DataFrame, ports: pd.DataFrame | None = None, inbound_lanes: pd.DataFrame | None = None) -> OptimizationResult:
    """Allocate demand to open DCs, optionally sourcing their volume from import ports."""
    _validate(facilities, REQUIRED_FACILITY_COLUMNS, "Facilities")
    _validate(demand, REQUIRED_DEMAND_COLUMNS, "Demand")
    _validate(lanes, REQUIRED_LANE_COLUMNS, "Lanes")
    if (ports is None) != (inbound_lanes is None):
        raise ValueError("Provide both Ports and inbound lanes, or neither.")
    if ports is not None:
        _validate(ports, REQUIRED_PORT_COLUMNS, "Ports")
        _validate(inbound_lanes, REQUIRED_INBOUND_LANE_COLUMNS, "Inbound lanes")
    if (demand["annual_demand_units"] < 0).any() or (facilities["capacity_units"] < 0).any():
        raise ValueError("Demand and capacity must be non-negative.")
    open_facilities = _open(facilities)
    capacity = open_facilities.set_index("facility")["capacity_units"].astype(float).to_dict()
    eligible_lanes = lanes[lanes["facility"].isin(capacity)].copy()
    eligible_lanes["cost_per_unit"] = eligible_lanes["cost_per_unit"].astype(float)
    allocations, unmet = [], []
    for row in demand.sort_values("annual_demand_units", ascending=False).itertuples(index=False):
        remaining = float(row.annual_demand_units)
        for lane in eligible_lanes[eligible_lanes["customer"] == row.customer].sort_values("cost_per_unit").itertuples(index=False):
            quantity = min(remaining, capacity[lane.facility])
            if quantity:
                allocations.append({"facility": lane.facility, "customer": row.customer, "annual_units": quantity, "cost_per_unit": lane.cost_per_unit, "annual_transport_cost": quantity * lane.cost_per_unit})
                capacity[lane.facility] -= quantity
                remaining -= quantity
            if remaining <= 1e-9:
                break
        if remaining > 1e-9:
            unmet.append({"customer": row.customer, "unmet_units": remaining})
    shipments = pd.DataFrame(allocations, columns=["facility", "customer", "annual_units", "cost_per_unit", "annual_transport_cost"])
    summary = open_facilities[["facility", "capacity_units", "fixed_annual_cost"]].copy()
    used = shipments.groupby("facility")["annual_units"].sum() if not shipments.empty else pd.Series(dtype=float)
    transport = shipments.groupby("facility")["annual_transport_cost"].sum() if not shipments.empty else pd.Series(dtype=float)
    summary["assigned_units"] = summary["facility"].map(used).fillna(0.0)
    summary["remaining_capacity"] = summary["capacity_units"] - summary["assigned_units"]
    summary["utilization_pct"] = (100 * summary["assigned_units"] / summary["capacity_units"].replace(0, pd.NA)).fillna(0.0)
    summary["transport_cost"] = summary["facility"].map(transport).fillna(0.0)
    unmet_demand = pd.DataFrame(unmet, columns=["customer", "unmet_units"])
    inbound = pd.DataFrame(columns=["port", "facility", "annual_units", "cost_per_unit", "annual_inbound_cost"])
    port_summary = pd.DataFrame(columns=["port", "capacity_units", "fixed_annual_cost", "assigned_units", "remaining_capacity", "utilization_pct", "inbound_transport_cost"])
    unmet_inbound = pd.DataFrame(columns=["facility", "unmet_inbound_units"])
    if ports is not None:
        inbound, port_summary, unmet_inbound = _allocate_inbound(summary, ports, inbound_lanes)
    outbound_cost = float(shipments["annual_transport_cost"].sum()) if not shipments.empty else 0.0
    inbound_cost = float(inbound["annual_inbound_cost"].sum()) if not inbound.empty else 0.0
    facility_fixed = float(open_facilities["fixed_annual_cost"].astype(float).sum())
    port_fixed = float(port_summary["fixed_annual_cost"].astype(float).sum()) if not port_summary.empty else 0.0
    kpis = {"total_demand_units": float(demand["annual_demand_units"].sum()), "served_units": float(shipments["annual_units"].sum()) if not shipments.empty else 0.0, "unmet_units": float(unmet_demand["unmet_units"].sum()) if not unmet_demand.empty else 0.0, "unmet_inbound_units": float(unmet_inbound["unmet_inbound_units"].sum()) if not unmet_inbound.empty else 0.0, "transport_cost": outbound_cost, "inbound_transport_cost": inbound_cost, "fixed_cost": facility_fixed, "port_fixed_cost": port_fixed, "total_cost": outbound_cost + inbound_cost + facility_fixed + port_fixed}
    return OptimizationResult(shipments, summary, kpis, unmet_demand, inbound, port_summary, unmet_inbound)

def to_excel(result: OptimizationResult) -> bytes:
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result.shipments.to_excel(writer, sheet_name="Outbound shipments", index=False)
        result.inbound_shipments.to_excel(writer, sheet_name="Inbound shipments", index=False)
        result.facility_summary.to_excel(writer, sheet_name="Facilities", index=False)
        result.port_summary.to_excel(writer, sheet_name="Ports", index=False)
        pd.DataFrame([result.kpis]).to_excel(writer, sheet_name="Summary", index=False)
        result.unmet_demand.to_excel(writer, sheet_name="Unmet outbound", index=False)
        result.unmet_inbound.to_excel(writer, sheet_name="Unmet inbound", index=False)
    return buffer.getvalue()
