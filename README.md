# OpenSupply

**Free, explainable logistics network analysis for small teams and classrooms.**

OpenSupply turns a distribution-network case study into a practical starting point: upload simple CSVs, test which distribution centers are open, and get capacity-aware shipment assignments, costs, utilization, and an Excel export.

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

## Method and limits

The first release uses a transparent greedy allocation: each customer is served by its lowest-cost eligible facility until capacity is full, then the next least-cost facility. It can split demand across facilities and flags unserved demand. It does not yet model route schedules, LTL/FTL breakpoints, lead times, or true mixed-integer facility selection.

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
