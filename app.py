import pandas as pd
import streamlit as st

from opensupply.optimizer import optimize_network, to_excel

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

try:
    facilities = load(facility_upload, "facilities.csv")
    demand = load(demand_upload, "demand.csv")
    lanes = load(lanes_upload, "lanes.csv")
    result = optimize_network(facilities, demand, lanes)
except (ValueError, pd.errors.ParserError) as error:
    st.error(str(error))
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Annual cost", f"${result.kpis['total_cost']:,.0f}")
c2.metric("Transportation", f"${result.kpis['transport_cost']:,.0f}")
c3.metric("Demand served", f"{result.kpis['served_units']:,.0f} units")
c4.metric("Unmet demand", f"{result.kpis['unmet_units']:,.0f} units")
if result.kpis["unmet_units"]:
    st.warning("This network cannot serve all demand. Open more capacity or revise lane coverage.")

left, right = st.columns(2)
with left:
    st.subheader("Facility utilization")
    st.bar_chart(result.facility_summary.set_index("facility")[["utilization_pct"]])
with right:
    st.subheader("Annual cost by facility")
    st.bar_chart(result.facility_summary.set_index("facility")[["transport_cost", "fixed_annual_cost"]])

st.subheader("Recommended shipment assignments")
st.dataframe(result.shipments, use_container_width=True, hide_index=True)
st.download_button("Export analysis to Excel", to_excel(result), "opensupply_network_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Inspect loaded inputs"):
    tabs = st.tabs(["Facilities", "Demand", "Lanes"])
    tabs[0].dataframe(facilities, hide_index=True)
    tabs[1].dataframe(demand, hide_index=True)
    tabs[2].dataframe(lanes, hide_index=True)
