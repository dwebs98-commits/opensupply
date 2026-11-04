import pandas as pd
from opensupply.optimizer import optimize_network
from opensupply.shipment_costing import cost_shipments

def test_cheapest_feasible_allocation_and_costs():
    facilities = pd.DataFrame({"facility": ["A", "B"], "capacity_units": [50, 100], "fixed_annual_cost": [10, 20], "open": [True, True]})
    demand = pd.DataFrame({"customer": ["C"], "annual_demand_units": [80]})
    lanes = pd.DataFrame({"facility": ["A", "B"], "customer": ["C", "C"], "cost_per_unit": [1, 2]})
    result = optimize_network(facilities, demand, lanes)
    assert result.kpis["served_units"] == 80
    assert result.kpis["total_cost"] == 140
    assert result.shipments.set_index("facility").loc["A", "annual_units"] == 50

def test_unmet_demand_is_reported():
    facilities = pd.DataFrame({"facility": ["A"], "capacity_units": [10], "fixed_annual_cost": [0], "open": [True]})
    demand = pd.DataFrame({"customer": ["C"], "annual_demand_units": [12]})
    lanes = pd.DataFrame({"facility": ["A"], "customer": ["C"], "cost_per_unit": [1]})
    assert optimize_network(facilities, demand, lanes).kpis["unmet_units"] == 2

def test_import_ports_add_inbound_cost_and_respect_port_capacity():
    facilities = pd.DataFrame({"facility": ["A"], "capacity_units": [100], "fixed_annual_cost": [0], "open": [True]})
    demand = pd.DataFrame({"customer": ["C"], "annual_demand_units": [80]})
    lanes = pd.DataFrame({"facility": ["A"], "customer": ["C"], "cost_per_unit": [1]})
    ports = pd.DataFrame({"port": ["P1", "P2"], "capacity_units": [50, 100], "fixed_annual_cost": [10, 20], "open": [True, True]})
    inbound_lanes = pd.DataFrame({"port": ["P1", "P2"], "facility": ["A", "A"], "cost_per_unit": [2, 3]})
    result = optimize_network(facilities, demand, lanes, ports, inbound_lanes)
    assert result.kpis["inbound_transport_cost"] == 190
    assert result.kpis["total_cost"] == 300
    assert result.kpis["unmet_inbound_units"] == 0

def test_shipment_costing_selects_lowest_cost_mode_and_facility():
    shipments = pd.DataFrame({"shipment_id": ["S1", "S2"], "destination_zip": ["11111", "22222"], "weight_lbs": [1000, 20000], "pallet_equivalents": [1, 20]})
    facilities = pd.DataFrame({"facility": ["A", "B"], "open": [True, True]})
    mileage = pd.DataFrame({"facility": ["A", "B", "A", "B"], "destination_zip": ["11111", "11111", "22222", "22222"], "distance_miles": [100, 200, 500, 100]})
    ltl = pd.DataFrame({"facility": ["A", "B"], "min_miles": [0, 0], "max_miles": [1000, 1000], "min_weight_lbs": [0, 0], "max_weight_lbs": [15999, 15999], "rate_per_lb": [0.1, 0.1]})
    tl = pd.DataFrame({"min_miles": [0], "max_miles": [1000], "rate_per_mile": [2]})
    fuel = pd.DataFrame({"facility": ["A", "B"], "ltl_fuel_pct": [0, 0], "tl_fuel_per_mile": [0, 0]})
    detail, exceptions, summary = cost_shipments(shipments, facilities, mileage, ltl, tl, fuel, tl_min_linehaul=0)
    assert exceptions.empty
    assert detail.set_index("shipment_id").loc["S1", "selected_mode"] == "LTL"
    assert detail.set_index("shipment_id").loc["S2", "selected_facility"] == "B"
    assert summary["tl_shipments"] == 1
