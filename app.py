import pandas as pd
import streamlit as st

from opensupply.optimizer import optimize_network, to_excel
from opensupply.shipment_costing import cost_shipments
from opensupply.scenarios import compare_scenarios

st.set_page_config(page_title="OpenSupply", page_icon="🚚", layout="wide")
st.title("OpenSupply")
st.caption("Free, explainable logistics network analysis for small teams and classrooms.")

def load(upload, filename):
    return pd.read_csv(upload) if upload else pd.read_csv(f"examples/{filename}")

with st.sidebar:
    st.header("Network inputs")
    st.caption("Upload CSVs matching the sample columns, or explore the included fictional network.")
    facility_upload = st.file_uploader("Facilities CSV", type="csv")
    demand_upload = st.file_uploader("Demand CSV", type="csv")
    lanes_upload = st.file_uploader("Lanes CSV", type="csv")
    ports_upload = st.file_uploader("Import ports CSV", type="csv")
    inbound_lanes_upload = st.file_uploader("Inbound port lanes CSV", type="csv")
    st.divider()
    st.header("Shipment costing inputs")
    shipment_upload = st.file_uploader("Shipments CSV", type="csv")
    shipment_mileage_upload = st.file_uploader("Shipment mileage CSV", type="csv")
    ltl_rates_upload = st.file_uploader("LTL rates CSV", type="csv")
    tl_rates_upload = st.file_uploader("TL rates CSV", type="csv")
    fuel_rates_upload = st.file_uploader("Shipment fuel rates CSV", type="csv")
    scenario_upload = st.file_uploader("Scenario comparison CSV", type="csv")

try:
    facilities = load(facility_upload, "facilities.csv")
    demand = load(demand_upload, "demand.csv")
    lanes = load(lanes_upload, "lanes.csv")
    ports = load(ports_upload, "ports.csv")
    inbound_lanes = load(inbound_lanes_upload, "inbound_lanes.csv")
except (ValueError, pd.errors.ParserError, FileNotFoundError) as error:
    st.error(str(error))
    st.stop()

st.subheader("Choose facilities for this scenario")
st.caption("Turn a facility on to include its capacity and annual fixed cost. Your changes affect this analysis only; they do not overwrite the uploaded file.")
facilities = facilities.copy()
facilities["open"] = facilities["open"].astype(str).str.lower().isin(["true", "1", "yes"])
facilities = st.data_editor(
    facilities,
    column_config={
        "facility": "Facility",
        "capacity_units": st.column_config.NumberColumn("Annual capacity", format="%,d"),
        "fixed_annual_cost": st.column_config.NumberColumn("Annual fixed cost", format="$%,d"),
        "open": st.column_config.CheckboxColumn("Include in scenario", help="Include this facility in the network calculation."),
    },
    disabled=["facility", "capacity_units", "fixed_annual_cost"],
    hide_index=True,
    key="facility_scenario",
    alt="Facilities available to include in the network scenario",
)

st.subheader("Choose import ports for this scenario")
st.caption("Turn a port on to include its inbound capacity and annual fixed cost. One inbound unit is assumed for every unit shipped from a facility.")
ports = ports.copy()
ports["open"] = ports["open"].astype(str).str.lower().isin(["true", "1", "yes"])
ports = st.data_editor(
    ports,
    column_config={
        "port": "Import port",
        "capacity_units": st.column_config.NumberColumn("Annual capacity", format="%,d"),
        "fixed_annual_cost": st.column_config.NumberColumn("Annual fixed cost", format="$%,d"),
        "open": st.column_config.CheckboxColumn("Include in scenario", help="Include this import port in the inbound cost calculation."),
    },
    disabled=["port", "capacity_units", "fixed_annual_cost"],
    hide_index=True,
    key="port_scenario",
    alt="Import ports available to include in the scenario",
)

try:
    result = optimize_network(facilities, demand, lanes, ports, inbound_lanes)
except ValueError as error:
    st.error(str(error))
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Annual cost", f"${result.kpis['total_cost']:,.0f}")
c2.metric("Outbound transport", f"${result.kpis['transport_cost']:,.0f}")
c3.metric("Inbound transport", f"${result.kpis['inbound_transport_cost']:,.0f}")
c4.metric("Demand served", f"{result.kpis['served_units']:,.0f} units")
c5.metric("Unmet inbound", f"{result.kpis['unmet_inbound_units']:,.0f} units")
if result.kpis["unmet_units"] or result.kpis["unmet_inbound_units"]:
    st.warning("The network cannot fully serve demand or source the assigned facility volume. Open more facility or port capacity, or revise lane coverage.")

left, right = st.columns(2)
with left:
    st.subheader("Facility utilization")
    st.bar_chart(result.facility_summary.set_index("facility")[["utilization_pct"]])
with right:
    st.subheader("Annual cost by facility")
    st.bar_chart(result.facility_summary.set_index("facility")[["transport_cost", "fixed_annual_cost"]])

st.subheader("Recommended shipment assignments")
st.dataframe(result.shipments, hide_index=True, alt="Recommended annual shipment assignments")
st.subheader("Recommended port-to-facility assignments")
st.dataframe(result.inbound_shipments, hide_index=True, alt="Recommended annual inbound port assignments")
st.download_button("Export analysis to Excel", to_excel(result), "opensupply_network_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Inspect loaded inputs"):
    tabs = st.tabs(["Facilities", "Demand", "Outbound lanes", "Ports", "Inbound lanes"])
    tabs[0].dataframe(facilities, hide_index=True)
    tabs[1].dataframe(demand, hide_index=True)
    tabs[2].dataframe(lanes, hide_index=True)
    tabs[3].dataframe(ports, hide_index=True)
    tabs[4].dataframe(inbound_lanes, hide_index=True)

st.divider()
st.header("Shipment costing foundation")
st.caption("Fictional shipment data is loaded by default. The tool evaluates every open-facility option, compares eligible LTL and TL costs, and keeps the lowest-cost option.")
rule_cols = st.columns(4)
with rule_cols[0]:
    ltl_max_weight = st.number_input("Maximum LTL weight (lb)", min_value=1, value=15999, step=1, key="ltl_max_weight")
with rule_cols[1]:
    trailer_capacity = st.number_input("53-ft trailer capacity (PE)", min_value=1, value=26, step=1, key="trailer_capacity")
with rule_cols[2]:
    container_capacity = st.number_input("40-ft container capacity (PE)", min_value=1, value=20, step=1, key="container_capacity")
with rule_cols[3]:
    tl_minimum = st.number_input("TL minimum linehaul ($)", min_value=0, value=700, step=50, key="tl_minimum")

try:
    shipment_data = load(shipment_upload, "shipments.csv")
    shipment_mileage = load(shipment_mileage_upload, "shipment_mileage.csv")
    ltl_rates = load(ltl_rates_upload, "ltl_rates.csv")
    tl_rates = load(tl_rates_upload, "tl_rates.csv")
    shipment_fuel = load(fuel_rates_upload, "fuel_rates.csv")
    shipment_detail, shipment_exceptions, shipment_summary = cost_shipments(
        shipment_data, facilities, shipment_mileage, ltl_rates, tl_rates, shipment_fuel,
        ltl_max_weight=ltl_max_weight, trailer_capacity_pe=trailer_capacity,
        tl_min_linehaul=tl_minimum,
    )
except (ValueError, pd.errors.ParserError, FileNotFoundError) as error:
    st.error(f"Shipment costing inputs are temporarily unavailable: {error}")
    st.info("The app will use the published fictional templates after this deployment refreshes. Please reload in a minute.")
else:
    metric_cols = st.columns(5)
    metric_cols[0].metric("Shipments costed", f"{shipment_summary['shipments_costed']:,.0f}")
    metric_cols[1].metric("Outbound cost", f"${shipment_summary['total_outbound_cost']:,.0f}")
    metric_cols[2].metric("LTL shipments", f"{shipment_summary['ltl_shipments']:,.0f}")
    metric_cols[3].metric("TL shipments", f"{shipment_summary['tl_shipments']:,.0f}")
    metric_cols[4].metric("Unpriced shipments", f"{shipment_summary['unpriced_shipments']:,.0f}")
    if shipment_summary["unpriced_shipments"]:
        st.warning("Some shipments could not be costed. Add a mileage, rate, or fuel rule for every open-facility option.")
    st.subheader("Lowest-cost shipment assignments")
    st.dataframe(shipment_detail, hide_index=True, alt="Lowest-cost facility and mode assignment for each shipment")
    if not shipment_exceptions.empty:
        st.subheader("Shipment exceptions")
        st.dataframe(shipment_exceptions, hide_index=True, alt="Shipments missing a valid assignment")
    st.download_button("Export shipment costing results", shipment_detail.to_csv(index=False).encode("utf-8"), "opensupply_shipment_costing.csv", "text/csv")

st.divider()
st.header("Scenario comparison")
st.caption("Fictional sample assumptions inspired by a logistics case study. Edit the values for a baseline, two-port recommendation, and three-port feasibility check.")
try:
    scenario_inputs = load(scenario_upload, "scenarios.csv")
    scenario_inputs = st.data_editor(
        scenario_inputs,
        column_config={
            "scenario": "Scenario",
            "purpose": "Purpose",
            **{column: st.column_config.NumberColumn(column.replace("_", " ").title(), format="$%,d") for column in ["outbound_freight", "inbound_freight", "port_management", "facility_rent", "facility_operating", "one_time_implementation"]},
            "total_pe": st.column_config.NumberColumn("Total PE", format="%,d"),
            "total_weight_lbs": st.column_config.NumberColumn("Total weight (lb)", format="%,d"),
            "service_1_day": st.column_config.NumberColumn("1-day service", format="percent"),
            "service_2_day": st.column_config.NumberColumn("2-day service", format="percent"),
            "service_3_day": st.column_config.NumberColumn("3-day service", format="percent"),
        },
        hide_index=True,
        key="scenario_inputs",
        alt="Editable annual cost assumptions for logistics scenarios",
    )
    scenario_results = compare_scenarios(scenario_inputs)
except (ValueError, pd.errors.ParserError, FileNotFoundError) as error:
    st.error(f"Scenario comparison inputs are unavailable: {error}")
else:
    display_columns = ["scenario", "purpose", "annual_cost", "annual_savings", "one_time_implementation", "payback_years", "five_year_net_savings", "cost_per_pe", "cost_per_lb", "service_1_day", "service_2_day", "service_3_day"]
    st.subheader("Baseline, two-port, and three-port comparison")
    st.dataframe(
        scenario_results[display_columns], hide_index=True,
        column_config={
            **{column: st.column_config.NumberColumn(column.replace("_", " ").title(), format="$%,.0f") for column in ["annual_cost", "annual_savings", "one_time_implementation", "five_year_net_savings"]},
            "payback_years": st.column_config.NumberColumn("Payback years", format="%.1f"),
            "cost_per_pe": st.column_config.NumberColumn("Cost per PE", format="$%.2f"),
            "cost_per_lb": st.column_config.NumberColumn("Cost per lb", format="$%.2f"),
            "service_1_day": st.column_config.NumberColumn("1-day service", format="percent"),
            "service_2_day": st.column_config.NumberColumn("2-day service", format="percent"),
            "service_3_day": st.column_config.NumberColumn("3-day service", format="percent"),
        },
        alt="Annual cost, savings, payback, and service comparison across scenarios",
    )
    st.download_button("Export scenario comparison", scenario_results.to_csv(index=False).encode("utf-8"), "opensupply_scenarios.csv", "text/csv")
