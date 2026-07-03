# PBTES for Solar Galvanizing — Simulation Framework

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

Simulation framework for a **concentrating solar thermal plant with Packed Bed Thermal Energy Storage (PBTES)** delivering industrial process heat to a hot-dip zinc galvanizing facility.

This repository is shared for **coauthor review** as part of a manuscript in preparation. All results are preliminary and subject to revision following coauthor input.

> For collaboration details, task assignments, and open questions, see [COAUTHOR_REPORT.md](COAUTHOR_REPORT.md).

---

## What Is This?

The study compares two solar thermal plant topologies, both using **Solar Salt** as HTF and **packed rock beds** for thermal energy storage:

| Topology | Storage | HX | Tanks |
|----------|---------|-----|-------|
| **PI (Parallel/Indirect)** | Decoupled via HX | Yes | 1 |
| **SD (Series/Direct)** | Primary loop in contact | No | 2 (series) |

The process load is a **150,000 kg zinc galvanizing bath** at 450°C, with a production schedule of Mon–Fri, 08:00–20:00.

A parametric sweep of 144 full-year simulations covers:
- Solar multiples SM = 0.5–3.5
- Tank geometries D = 4–20 m, H = 3–12 m
- Physical sensitivities (particle size, void fraction, insulation)
- HTF comparison: Solar Salt vs. Air

---

## Prerequisites

**Python 3.10 or higher** is required.

```bash
pip install -r requirements.txt
```

Key dependencies: `tespy`, `CoolProp`, `numpy`, `pandas`, `matplotlib`, `scipy`

> Solar Salt is modeled as `INCOMP::NaK` via CoolProp's incompressible mixture database — no additional setup needed.

---

## Quick Start

### Run a single simulation

```bash
# 7-day test (default)
python run_simulation.py

# Full-year baseline
python run_simulation.py --days 365 --tag baseline

# Series/Direct topology
python run_simulation.py --days 365 --topology Series --tank_config direct

# Custom geometry
python run_simulation.py --days 365 --aperture 1500 --diameter 9 --height 6
```

Results are saved to `results/` (gitignored):
```
results/baseline_Parallel_indirect_NaK_D7.0_H5.0_A1000_365d_YYYYMMDD.csv
```

### Run the parametric sweep

```bash
python run_parametric.py --sweep topology   # 2 jobs (fast check)
python run_parametric.py --sweep aperture   # aperture area sweep
python run_parametric.py --sweep full --days 365  # all 144 jobs (~24 h)
```

### Post-process results

```bash
python scripts/run_postprocess.py results/baseline_*.csv
python scripts/run_assessment_06_figures.py   # generate all figures
```

### Run tests

```bash
python -m pytest tests/ -x --tb=short
```

---

## Repository Structure

```
pbtes-solar-galvanizing/
│
├── run_simulation.py        ← Single simulation entry point
├── run_parametric.py        ← Parametric sweep entry point
├── requirements.txt
├── TMY.csv                  ← Weather data (Santiago, Chile TMY)
│
├── pbtes/                   ← Main Python package
│   ├── config.py            ← All parameters (single source of truth)
│   ├── components/
│   │   └── ptc_field.py     ← PTC model (TESPy extension)
│   ├── storage/
│   │   ├── packed_bed.py    ← 1D two-phase Schumann model
│   │   └── zinc_pool.py     ← Dynamic zinc pool model
│   ├── network/
│   │   └── system.py        ← TESPy network builder (PI and SD modes)
│   ├── simulation/
│   │   ├── solver.py        ← Quasi-steady orchestrator
│   │   └── winter_logic.py  ← Freeze-protection seasonal control
│   ├── reporting/
│   │   └── plots.py         ← Figures and CSV output
│   └── analysis/
│       ├── economics.py     ← LCOH calculator
│       ├── postprocess.py   ← Pump power, net solar fraction
│       └── results_reader.py
│
├── scripts/                 ← Post-processing pipeline
│   ├── run_postprocess.py
│   ├── run_aggregate_metrics.py
│   ├── run_assessment_06_figures.py
│   ├── run_economic_sensitivity.py
│   ├── run_exergoeconomics.py
│   └── sweep_dashboard.py   ← Interactive results GUI
│
├── tests/                   ← Pytest test suite
│
├── paper/                   ← Manuscript and figures
│   ├── Manuscript_v3.tex    ← Current LaTeX draft (preliminary)
│   └── figures/             ← PDF figures (preliminary)
│
├── docs/                    ← Methodology documentation
│   ├── PHYSICS_METHODOLOGY.md
│   ├── ECONOMIC_METHODOLOGY.md
│   ├── PROJECT_CONTEXT.md
│   └── zinc_pool_model_methodology.md
│
└── COAUTHOR_REPORT.md       ← Research questions, methodology, open tasks
```

---

## Key Parameters

All parameters are centralized in [`pbtes/config.py`](pbtes/config.py):

```python
from pbtes.config import baseline_config
cfg = baseline_config()
```

| Parameter | Baseline value |
|-----------|---------------|
| Aperture area | 1,000 m² |
| Tank D × H | 7.0 m × 5.0 m |
| Particle diameter d_p | 50 mm |
| Void fraction ε | 0.40 |
| Solar Salt T range | 300–600°C |
| Process heat demand | ≈450 kW |
| Zinc bath mass | 150,000 kg |
| Discount rate | 8% / 25 yr |

---

## Documentation

| Document | Purpose |
|----------|---------|
| [COAUTHOR_REPORT.md](COAUTHOR_REPORT.md) | Research questions, methodology summary, open tasks per coauthor |
| [docs/PHYSICS_METHODOLOGY.md](docs/PHYSICS_METHODOLOGY.md) | Mathematical models, Schumann PDE, coupling framework |
| [docs/ECONOMIC_METHODOLOGY.md](docs/ECONOMIC_METHODOLOGY.md) | LCOH formulation, CAPEX correlations |
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | Full project reference and parameters |
| [paper/Manuscript_v3.tex](paper/Manuscript_v3.tex) | LaTeX manuscript draft (preliminary) |

---

## Status

This is a **work in progress**. The methodology is complete; the results sections are a first draft pending:
- Coauthor review of PTC model, PBTES correlation, and economic assumptions
- Re-runs of 14 flagged simulation jobs
- Joint decisions on journal target and final parameter values

See [COAUTHOR_REPORT.md](COAUTHOR_REPORT.md) for the full list of open items.

---

## Authors

Ian Wolde, Eduardo González-Mora, Felipe G. Battisti, Rodrigo Escobar, José M. Cardemil

*Pontificia Universidad Católica de Chile — SERC Chile*

---

## Citation

Manuscript in preparation. Citation to be added upon publication.
