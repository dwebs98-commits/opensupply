import pandas as pd
from opensupply.scenarios import compare_scenarios

def test_scenario_savings_and_payback():
    scenarios = pd.DataFrame([
        {"scenario":"Base","purpose":"Baseline","outbound_freight":100,"inbound_freight":100,"port_management":0,"facility_rent":0,"facility_operating":0,"one_time_implementation":0,"total_pe":10,"total_weight_lbs":100,"service_1_day":0,"service_2_day":0,"service_3_day":0},
        {"scenario":"Plan","purpose":"Plan","outbound_freight":50,"inbound_freight":100,"port_management":0,"facility_rent":0,"facility_operating":0,"one_time_implementation":75,"total_pe":10,"total_weight_lbs":100,"service_1_day":0,"service_2_day":0,"service_3_day":0},
    ])
    result = compare_scenarios(scenarios)
    assert result.loc[1, "annual_savings"] == 50
    assert result.loc[1, "payback_years"] == 1.5
    assert result.loc[1, "five_year_net_savings"] == 175
