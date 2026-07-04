# PBTES + Solar Galvanizing — Coauthor Collaboration Report
*Ian Wolde | July 2026 | Internal document — not for submission*

> **Note on results**: All quantitative outputs are **preliminary**. Once each coauthor has reviewed and provided their input, the full simulation suite will be re-run with corrected models, updated parameters, and validated correlations. The numbers shown here are for orientation only.

> **AI disclosure**: This document and the accompanying email were drafted with assistance from Claude (Anthropic). Technical content, scientific criteria, and editorial decisions are the responsibility of the author.

---

## Resources

| Item | Location |
|------|----------|
| **Manuscript (PDF)** | Attached to the invitation email |
| **Code + figures + methodology docs** | https://github.com/entropian-pc/pbtes-solar-galvanizing |
| **Manuscript source (LaTeX)** | `paper/Manuscript_v3.tex` in the repo |
| **This report** | `COAUTHOR_REPORT.md` in the repo |

---

## 1. Research Questions

This paper addresses five research questions (RQs):

| RQ | Question |
|----|----------|
| **RQ1** | Which topology (PI vs. SD) delivers higher solar fraction and lower LCOH at the same design point? |
| **RQ2** | How does the solar multiple (aperture area) affect solar fraction, LCOH, and TES utilization? |
| **RQ3** | What is the cost-optimal tank geometry (D × H) for the packed bed? |
| **RQ4** | How robust is annual performance to packed-bed physical parameters (particle size, void fraction, insulation)? |
| **RQ5** | What is the benefit of Solar Salt over Air as HTF, in terms of solar fraction and economics? |

---

## 2. Proposed System

The study evaluates a **hypothetical solar thermal plant** designed to supply process heat to a hot-dip zinc galvanizing facility in Santiago, Chile. The plant has three coupled subsystems:

### 2.1 Solar Field
- **Parabolic Trough Collectors (PTC)**, aperture area 1,000 m² at baseline (swept 500–3,500 m²)
- HTF: **Solar Salt** (commercial NaK nitrate mixture, modeled via CoolProp as `INCOMP::NaK`)
- Operating range: 300–600°C; design outlet: 560°C

### 2.2 Packed Bed Thermal Energy Storage (PBTES)
- 1D two-phase **Schumann model** (analytical eigenvalue solution, 20 spatial nodes)
- Baseline geometry: **D = 7 m, H = 5 m** (swept D = 4–20 m, H = 3–12 m)
- Fill: rock/ceramic, d_p = 50 mm, ε = 0.40, ρ_s = 3,500 kg/m³
- HTC: **Wakao-Kaguei** correlation (Nu = 2.0 + 1.1 Re^0.6 Pr^(1/3))
- State of charge normalized between cold reference (400°C uniform) and hot reference (560°C uniform)

### 2.3 Zinc Galvanizing Process
- **Dynamic lumped-capacitance** model: 150,000 kg molten zinc, target 450°C
- Production load: 5,000 kg/h steel from 25°C, Mon–Fri 08:00–20:00
- Process heat demand: ≈450 kW continuous during production
- Coupled to the HTF loop via a process heat exchanger (offdesign TTD = 20 K)

### 2.4 Two Plant Topologies Compared

**Parallel/Indirect (PI)** — The primary loop can split after the PTC. The PBTES is charged via a dedicated HX (thermally decoupled from the primary loop). A separate discharge HX connects storage to the process. One PBTES tank.

**Series/Direct (SD)** — The primary Solar Salt flows in a single loop: PTC → Hot Tank (PBTES) → Process → Cold Tank (PBTES) → PTC. No intermediate HX. Two PBTES tanks in series.

---

## 3. Simulation Methodology

### 3.1 Quasi-Steady Coupling Framework
At each hourly timestep:
1. **Operating mode selected** — based on irradiance thresholds, SoC, and tank temperatures
2. **TESPy network solved** — steady-state thermodynamic loop for the active mode; returns mass flows and temperatures
3. **1D Schumann model stepped** — boundary conditions from TESPy; returns updated temperature profile and SoC
4. **Zinc pool model stepped** — integrates energy balance with HX heat transfer from step 2
5. **Convergence check** — iterates steps 2–4 until TES return temperature converges (tol: 1e-3 K)

### 3.2 Operating Modes

**PI — 4 active modes:**
| Mode | Name | Condition |
|------|------|-----------|
| 2 | Solar-Only | E ≥ E_proc, TES full or Mode 5/6 not viable |
| 3 | TES-Discharge | No sun, SoC > 0.10, T_top ∈ 500–580°C |
| 4 | Auxiliary | No sun, SoC < 0.05 |
| 5 | Solar-Charge | E ≥ E_charge, T_bot cold enough, SoC < 0.90 |
| 6 | Decoupled-Charge | E ≥ E_charge, SoC < 0.80, Mode 5 not viable (sticky) |

**SD — 4 active modes:**
| Mode | Name | Condition |
|------|------|-----------|
| 1 | Solar-Charge | E ≥ E_charge, SoC < 0.99, T_ptc > T_top |
| 2 | Solar-Only | E ≥ E_proc, TES full |
| 3 | TES-Discharge | No sun, SoC > 0.10, T_top ∈ 500–580°C |
| 4 | Auxiliary | Fallback |

### 3.3 Parametric Sweep
- **144 full-year jobs** (365 days × 8760 hours each)
- Parallelized across 8 workers; ≈1.3 CPU-h per job
- Sweep groups: aperture area (SM 0.5–3.5), D×H geometry grid (PI: 63 pts, SD: 22 pts), physical sensitivities, HTF comparison
- 136/144 (94.4%) completed; 8 SD large-tank jobs under re-run

### 3.4 Performance Metrics
Solar fraction (thermal and net), LCOH (annualized CAPEX + OPEX / delivered heat), round-trip efficiency, mode-hour distribution, mean storage temperature.

### 3.5 LCOH Model *(pending expert review — see Task B)*
CAPEX: PTC ($200/m²), tank ($500/m³ structure + $2/kg HTF + $0.10/kg fill), pumps, HX (stub: $50,000/unit fixed).
OPEX: electricity for pumping, auxiliary heater fuel, 2% O&M.
Discount rate: 8%, lifetime: 25 yr.
**Note**: PTC cost ($200 vs. $300/m²) and electricity tariff ($0.10 vs. $0.17/kWh) are inconsistent between the manuscript and the ECONOMIC_METHODOLOGY.md document. Decision needed.

---

## 4. What We Need — Tasks by Coauthor

---

### Eduardo González-Mora — PTC Model Verification

**Background**: The PTC model in `pbtes/components/ptc_field.py` is a Python re-implementation of the TESPy model originally developed by Eduardo. It uses:
- Net power: `Q_ptc = A [E · η_opt · K(θ) − q_losses]`
- IAM: `K(θ) = 1 + i₁θ + i₂θ²` with i₁ = −1.59×10⁻³, i₂ = 9.77×10⁻⁵
- Receiver losses: `q_losses = c₁ΔT + c₂ΔT²` with c₁ = 0.0622 W/m²K, c₂ = 0.00023 W/m²K²
- Design point: DNI = 900 W/m², T_amb = 20°C, AOI = 20°, η_opt = 0.816
- Offdesign: TESPy solves for mass flow and outlet temperature under fixed boundary conditions

**We need your review of**:
1. Are the optical and thermal loss coefficients correct for the intended collector model?
2. Does the offdesign formulation in TESPy correctly represent how the original model was intended to behave?
3. Are there additional loss terms (e.g., end losses, shadowing) that should be included or that are already accounted for in η_opt?

*Output requested*: Written comments on `ptc_field.py` and/or the equations in §3.1 of the manuscript draft.

---

### Ignacio Calderón-Vásquez — Economic Methodology Review

**Background**: The LCOH calculation is built on capital cost correlations, CEPCI escalation, and a simple CRF annualization. There are two active inconsistencies that need resolution before the final run:

1. **PTC cost**: manuscript uses $200/m² vs. ECONOMIC_METHODOLOGY.md recommends $300/m² (Akar & Kurup 2025).
2. **Electricity tariff**: manuscript uses $0.10/kWh vs. $0.17/kWh (Chilean industrial tariff, 2024).
3. **HX cost model**: currently a fixed stub of $50,000/unit regardless of duty. Needs a UA-based cost correlation so it scales with tank size and aperture area. This is important because at large tank volumes, the HX is a significant fraction of CAPEX.

**We need your input on**:
1. Which cost values are appropriate for the Santiago/Chile context and publication year?
2. Is there a published UA-based HX cost correlation we should use?
3. Are there other economic assumptions you'd flag as inconsistent with the literature?

*Output requested*: Revised parameter table and/or co-writing §Economic Analysis and the economic sensitivity section.

---

### Felipe Battisti — PBTES Correlation Assessment

**Background**: The packed-bed model uses the **Wakao-Kaguei correlation**:

> Nu = 2.0 + 1.1 Re^0.6 Pr^(1/3)

This was validated for air at Re_p = 15–8,500. At our baseline Solar Salt conditions (SM=1, low flow rate), **Re_p < 1** — well outside the validated range. We use it as the best available single-phase correlation but acknowledge this as an open limitation.

Full set of questions in `context/coauthor_felipe_pbtes_request.md`. Summary:
1. Is Wakao-Kaguei defensible for Solar Salt at Re < 1? What uncertainty band should we attach to h_sf?
2. Is there a more appropriate correlation for liquid-metal or high-Pr fluid packed beds at low Re?
3. Does the single-phase model (no radiation term) introduce meaningful error at 500°C+?
4. Is there an appropriate wall-HTC correction for the tank boundary nodes?

**Impact**: The HTC directly affects thermocline sharpness, charging effectiveness, and thus solar fraction. A 50% change in h_sf would propagate into the results — if Wakao-Kaguei over- or under-predicts by that margin at Re < 1, we need to know before reporting results.

*Output requested*: Written assessment for §3.2 (validation paragraph). If a better correlation is available and straightforward to implement, we can incorporate it into the model before the final run.

---

### Rodrigo Escobar & José M. Cardemil — Supervision & Open Decisions

The following questions need a group decision before we finalize the simulation configuration and write §5 Results:

1. **Target journal** — The manuscript currently has *Energy Conversion and Management* in the preamble; the planning documents list *Journal of Energy Storage*, *Energy*, and *Solar Energy*. Word limits, figure counts, and supplementary rules differ.

2. **LCOH U-shape boundary** — At the baseline aperture, LCOH continues decreasing at D = 20 m (the largest simulated tank). Options: (a) report "no minimum found within the practical range" and bound by construction/land cost arguments; (b) extend the sweep to D = 22–25 m to locate the minimum explicitly.

3. **SD geometry density** — The SD D×H grid has 22 points vs. 63 for PI. After re-runs, is this sufficient for a contour figure of comparable resolution, or should we add SD points?

4. **Manuscript framing** — Should the paper emphasize the PI vs. SD topology comparison as the primary contribution (novel system-level study for industrial solar galvanizing), or should PBTES optimization (D×H geometry, robustness) be the primary message?

*Output requested*: Guidance on the above decisions; high-level review of §1 Introduction framing once available.

---

## 5. Current Manuscript Status

| Section | Status | Responsible |
|---------|--------|-------------|
| §1 Introduction | Draft — needs explicit gap statement | Ian + Ignacio |
| §2 System Description | Complete draft | Ian |
| §3 Mathematical Models | Complete draft — **PTC: pending Eduardo; PBTES correlation: pending Felipe** | Ian |
| §4 Case Study | First draft | Ian |
| §5 Results | First draft — **all numbers preliminary; final run after coauthor input** | Ian |
| §6 Conclusions | First draft — preliminary | Ian |
| Economic section | Draft — **parameter values pending Ignacio** | Ian + Ignacio |
| Abstract | Draft | Ian |
| Nomenclature | Partial | Ian |

---

*Any comments are welcome by email. A group meeting will be scheduled upon Ian's return from vacation to make joint decisions on the open questions and plan the final simulation run.*
