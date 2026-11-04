# OpenSupply

**Free, explainable logistics network analysis for small teams and classrooms.**

OpenSupply turns a distribution-network case study into a practical starting point: upload simple CSVs, test which distribution centers are open, and get capacity-aware shipment assignments, costs, utilization, and an Excel report.

The included data is fictional. This project deliberately contains no NT Logistics proprietary data, rates, customer names, or network details.

## First release

- Facility capacity and fixed-cost modeling
- Customer demand and lane-cost inputs
- Least-cost, capacity-aware shipment allocations
- Annual transportation, fixed, and total cost reporting
- Facility utilization chart and unmet-demand warning
- Excel export of the full analysis

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## CSV inputs

| File | Required columns |
| --- | --- |
| `facilities.csv` | `facility`, `capacity_units`, `fixed_annual_cost`, `open` |
| `demand.csv` | `customer`, `annual_demand_units` |
| `lanes.csv` | `facility`, `customer`, `cost_per_unit` |

Use `TRUE` or `FALSE` for `open`. Costs and quantities represent annual planning values.

## Run scenarios in the app

Open facilities can be changed directly in the app—no spreadsheet editing is required.

In **Choose facilities for this scenario**, use the **Include in scenario** checkbox to turn each facility on or off. The app immediately recalculates shipment assignments, facility utilization, transportation cost, total annual cost, and unmet demand.

Your checkbox changes apply only to the current browser session. They do not overwrite your uploaded CSV file.

### Working with larger networks

OpenSupply is not limited to the included three-facility example. You can upload any number of:

- Facilities in `facilities.csv`
- Customers in `demand.csv`
- Facility-to-customer lanes in `lanes.csv`

Every customer must have at least one transportation lane from an included facility. If no included facility can serve a customer—or available capacity is insufficient—the app reports the remaining quantity as unmet demand.

## Live app

Try OpenSupply at [opensupply.streamlit.app](https://opensupply.streamlit.app/).

## Method and limits

The first release uses a transparent greedy allocation: each customer is served by its lowest-cost eligible facility until capacity is full, then the next least-cost facility. It can split demand across facilities, but it does not guarantee a globally optimal solution.

## Roadmap

1. Current-versus-proposed scenario manager
2. Map-based lane visualization and distance-based default costs
3. Solver-backed optimization with service and capacity constraints
4. Demand forecasting, inventory, EOQ, and reorder-point modules
5. Deployment guide and contribution-ready issue templates

## Contributing

Contributions are welcome. Please open an issue with a reproducible example or clear proposal before larger changes.

## License

[MIT](LICENSE)
