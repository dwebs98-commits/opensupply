"""Shipment-level LTL/TL costing with lowest-cost open-facility assignment."""
from __future__ import annotations

import math
import pandas as pd

REQUIRED_SHIPMENTS = {"shipment_id", "destination_zip", "weight_lbs", "pallet_equivalents"}
REQUIRED_MILEAGE = {"facility", "destination_zip", "distance_miles"}
REQUIRED_LTL = {"facility", "min_miles", "max_miles", "min_weight_lbs", "max_weight_lbs", "rate_per_lb"}
REQUIRED_TL = {"min_miles", "max_miles", "rate_per_mile"}
REQUIRED_FUEL = {"facility", "ltl_fuel_pct", "tl_fuel_per_mile"}

def _require(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(sorted(missing))}")

def cost_shipments(shipments, facilities, mileage, ltl_rates, tl_rates, fuel_rates, *, ltl_max_weight=15999, trailer_capacity_pe=26, tl_min_linehaul=700):
    """Price every shipment from each open facility and retain the lowest valid option."""
    for frame, columns, name in [(shipments, REQUIRED_SHIPMENTS, "Shipments"), (mileage, REQUIRED_MILEAGE, "Mileage"), (ltl_rates, REQUIRED_LTL, "LTL rates"), (tl_rates, REQUIRED_TL, "TL rates"), (fuel_rates, REQUIRED_FUEL, "Fuel rates")]:
        _require(frame, columns, name)
    open_names = set(facilities[facilities["open"].astype(str).str.lower().isin(["true", "1", "yes"])]["facility"])
    mileage = mileage[mileage["facility"].isin(open_names)].copy()
    rows, exceptions = [], []
    for shipment in shipments.itertuples(index=False):
        options = []
        for lane in mileage[mileage["destination_zip"].astype(str).str.zfill(5) == str(shipment.destination_zip).zfill(5)].itertuples(index=False):
            distance = float(lane.distance_miles)
            fuel = fuel_rates[fuel_rates["facility"] == lane.facility]
            if fuel.empty:
                continue
            fuel = fuel.iloc[0]
            tl_row = tl_rates[(tl_rates["min_miles"] <= distance) & (tl_rates["max_miles"] >= distance)]
            if tl_row.empty:
                continue
            loads = max(1, math.ceil(float(shipment.pallet_equivalents) / trailer_capacity_pe))
            tl_linehaul = max(distance * float(tl_row.iloc[0].rate_per_mile), tl_min_linehaul) * loads
            tl_cost = tl_linehaul + distance * float(fuel.tl_fuel_per_mile) * loads
            options.append((tl_cost, "TL", lane.facility, distance, loads))
            if float(shipment.weight_lbs) <= ltl_max_weight:
                ltl = ltl_rates[(ltl_rates["facility"] == lane.facility) & (ltl_rates["min_miles"] <= distance) & (ltl_rates["max_miles"] >= distance) & (ltl_rates["min_weight_lbs"] <= shipment.weight_lbs) & (ltl_rates["max_weight_lbs"] >= shipment.weight_lbs)]
                if not ltl.empty:
                    ltl_cost = float(shipment.weight_lbs) * float(ltl.iloc[0].rate_per_lb) * (1 + float(fuel.ltl_fuel_pct))
                    options.append((ltl_cost, "LTL", lane.facility, distance, 0))
        if not options:
            exceptions.append({"shipment_id": shipment.shipment_id, "reason": "No valid open-facility lane, rate, or fuel rule"})
            continue
        cost, mode, facility, distance, loads = min(options, key=lambda option: option[0])
        rows.append({"shipment_id": shipment.shipment_id, "destination_zip": str(shipment.destination_zip).zfill(5), "weight_lbs": shipment.weight_lbs, "pallet_equivalents": shipment.pallet_equivalents, "selected_facility": facility, "selected_mode": mode, "distance_miles": distance, "tl_loads_required": loads, "selected_cost": cost, "options_evaluated": len(options)})
    detail = pd.DataFrame(rows, columns=["shipment_id", "destination_zip", "weight_lbs", "pallet_equivalents", "selected_facility", "selected_mode", "distance_miles", "tl_loads_required", "selected_cost", "options_evaluated"])
    exceptions = pd.DataFrame(exceptions, columns=["shipment_id", "reason"])
    summary = {"shipments_submitted": float(len(shipments)), "shipments_costed": float(len(detail)), "unpriced_shipments": float(len(exceptions)), "total_outbound_cost": float(detail["selected_cost"].sum()) if not detail.empty else 0.0, "ltl_shipments": float((detail["selected_mode"] == "LTL").sum()) if not detail.empty else 0.0, "tl_shipments": float((detail["selected_mode"] == "TL").sum()) if not detail.empty else 0.0}
    return detail, exceptions, summary
