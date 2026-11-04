import pandas as pd
from opensupply.optimizer import optimize_network

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
