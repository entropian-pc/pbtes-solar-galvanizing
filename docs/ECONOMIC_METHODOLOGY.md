# Economic & Cost Assessment Methodology

*Authoritative reference for capital cost estimation, LCOH calculation, and
exergoeconomic analysis of the PBTES solar thermal plant for galvanizing.*

---

## 1. Scope and Integration Assumptions

The economic assessment evaluates the incremental capital and operating costs of
integrating a solar field and thermal energy storage into an **existing zinc
galvanizing plant**. Costs already borne by the host facility — zinc bath
infrastructure, buildings, labour, existing natural gas connection — are excluded.

The system boundary includes:

1. Parabolic Trough Collector (PTC) solar field, fully installed
2. Packed Bed Thermal Energy Storage (PBTES) tank, complete with fill material, insulation, and civil works
3. Solar Salt heat transfer fluid inventory
4. All heat exchangers (charge, discharge, process immersed coil)
5. HTF circulation pumps with motors and VFDs
6. Interconnecting piping, valves, instrumentation, and controls
7. Engineering, procurement, construction (EPC) overhead and contingency

All costs are expressed in **2025 United States dollars (USD)** unless noted.
The Chemical Engineering Plant Cost Index (CEPCI) is used to escalate legacy
cost correlations to current-year values. The assumed CEPCI for 2025 is **800**
(base CEPCI = 500 for the Turton et al. correlation, ≈2006).

---

## 2. Parabolic Trough Collector (PTC) Field Cost

### 2.1 Specific Cost Correlation

The PTC solar field cost follows the economy-of-scale power law derived from the
NREL DFMA (Design for Manufacturing and Assembly) bottom-up model by
Akar and Kurup (2025) [@Akar2025]:

$$C_{\text{PTC}} \,[\text{USD}] = C_{\text{ref}} \cdot A_{\text{ptc}} \cdot \left( \frac{A_{\text{ptc}}}{A_{\text{ref}}} \right)^{n-1}$$

where:

| Symbol | Value | Description |
|--------|-------|-------------|
| $C_{\text{ref}}$ | 300 USD/m² | Reference specific cost at $A_{\text{ref}}$ = 1000 m² |
| $A_{\text{ptc}}$ | variable | Total aperture area [m²] |
| $n$ | 0.80 | Economy-of-scale exponent |

The installed cost includes manufacturing, assembly, site labour, and
foundations. A balance-of-plant (BOP) multiplier of **1.40** covers the HTF
subsystem, piping from field to process, controls integration, EPC overhead,
and contingency, consistent with NREL SAM cost models [@Turchi2013; @Kurup2015].

At the design-point aperture area of 1000 m², the total PTC field installed
cost is approximately **$420,000 USD**.

### 2.2 Cost Breakdown

Steel components (space frame, pylons, support arms) dominate at 52–54% of
solar field cost, followed by mirror panels (13%), receiver tubes (9%), site
labour (8%), foundations (5%), and drive hydraulics/controls (8%)
[@Akar2025]. This makes PTC costs sensitive to global steel prices, with a
potential 15–28% reduction if using Chinese-origin steel.

---

## 3. Packed Bed TES Tank Cost

### 3.1 Tank Vessel — Wall Thickness

The minimum wall thickness for a cylindrical pressure vessel is determined
according to ASME Boiler and Pressure Vessel Code Section VIII, Division 1,
paragraph UG-27 [@ASME_VIII]:

$$t_{\text{min}} = \frac{P \cdot R}{\sigma_{\text{allow}} \cdot E - 0.6P}$$

| Parameter | Value | Source |
|-----------|-------|--------|
| Design pressure $P$ | 0.5 MPa (5 bar) | process setpoint |
| Inner radius $R$ | 3.5 m (D = 7.0 m) | baseline design |
| Allowable stress $\sigma_{\text{allow}}$ | 50 MPa | ASME II-D SS316 at 600 °C |
| Weld joint efficiency $E$ | 0.85 | typical radiography |
| Corrosion allowance | 1.5 mm | molten nitrate salt |
| **Design thickness $t_{\text{design}}$** | **45 mm** | incl. fabrication tolerance |

The vessel material is **SS316 (A240-316)** plate, required for molten nitrate
salt compatibility at 550–600 °C [@Bradshaw2002]. Carbon steel is unacceptable
above ~425 °C in nitrate salt service due to corrosion rates exceeding 1 mm/yr.

### 3.2 Vessel Mass and Material Cost

| Component | Surface Area [m²] | Mass [kg] |
|-----------|-------------------|-----------|
| Cylindrical shell ($\pi$·7·5) | 110 | 39,600 |
| Bottom head (2:1 ellipsoidal) | 44 | 15,840 |
| Top head (2:1 ellipsoidal) | 44 | 15,840 |
| **Total** | **198** | **71,280** |

SS316 plate price: ~$5.50/kg (mid-2025, MEPS International indices).
Vessel material cost: **~$392,000 USD**.

### 3.3 Insulation System

A high-performance multi-layer insulation system is used for the 600 °C hot-face
temperature, with a total thickness of 1.0 m (matching the thermal model):

| Layer | Material | Thickness [mm] | Cost [USD/m²] |
|-------|----------|---------------|---------------|
| Hot face | Ceramic fibre blanket (1260 °C grade) | 200 | 55 |
| Mid | Microporous silica/aerogel board | 200 | 150 |
| Outer | Mineral wool | 500 | 40 |
| Cladding | Aluminium sheet 0.7 mm | — | 40 |

The thermal model uses an idealized effective conductivity
$k_{\text{ins}} = 0.012$ W/(m·K) for this composite system, representing
the high-performance microporous/aerogel class. Total material cost:
$285/m². Total insulated surface area: ~154 m². Installed insulation
cost: **~$66,000 USD**.

### 3.4 Fill Material

| Parameter | Value |
|-----------|-------|
| Bed volume ($\pi$·3.5²·5.0) | 192.4 m³ |
| Solid volume ($\varepsilon$ = 0.40) | 115.4 m³ |
| Solid mass ($\rho_s$ = 3500 kg/m³) | 404 tonnes |
| Crushed rock cost (delivered) | $60/tonne |
| **Fill cost (installed)** | **~$48,000 USD** |

Quartzite or basalt crushed rock (50 mm nominal) is used as the packed-bed
filler, consistent with prior experimental and modelling studies
[@Zanganeh2012; @Pelay2017].

### 3.5 Total Installed Tank Cost

Applying EPC multipliers from chemical process plant cost estimation
[@Turton2018; @Peters2004]:

| Item | Material [USD] | EPC Factor | Installed [USD] |
|------|---------------|------------|-----------------|
| SS316 vessel | 392,000 | 3.5 | 1,372,000 |
| Insulation (high-performance) | 43,900 | 1.5 | 65,800 |
| Fill material | 24,000 | 2.0 | 48,000 |
| Piping, valves, instrumentation | — | — | 180,000 |
| Civil works / foundation | — | — | 70,000 |
| Engineering + contingency (25%) | — | — | 434,000 |
| **TOTAL (one tank)** | | | **~2,170,000** |

**Thermal capacity:** ~58 MWh_th (ΔT = 300 K) → specific cost **~$37/kWh_th**,
consistent with the $30–40/kWh_th range reported by Glatzmaier (2011)
[@Glatzmaier2011] for thermocline tanks and the $15–25/kWh_th for utility-scale
packed beds by IRENA (2020) [@IRENA2020], with a scale penalty appropriate for
a sub-100 MWh_th system.

### 3.6 Number of Tanks

The number of tanks depends on the plant topology:
- **Parallel/Indirect (PI):** 1 tank (single packed bed with secondary loop)
- **Parallel/Direct (PD):** 2 tanks (Hot Tank + Cold Tank, direct contact)
- **Series/Direct (SD):** 2 tanks (Hot Tank + Cold Tank, in series)
- **Series/Indirect (SI):** 1 tank (single packed bed with secondary loop)

The cold tank in two-tank configurations may use carbon steel if the operating
temperature remains below ~425 °C, reducing cost by approximately 40%.

---

## 4. Heat Transfer Fluid (Solar Salt) Cost

### 4.1 Inventory Calculation

| Parameter | Value |
|-----------|-------|
| Tank volume | 192.4 m³ |
| Void fraction (salt-occupied) | 0.40 |
| Salt volume | 77.0 m³ |
| Salt density (avg 300–600 °C) | ~1875 kg/m³ |
| **Salt mass** | **~144 tonnes** |

### 4.2 Unit Price

The Solar Salt eutectic mixture (60 wt% NaNO₃ + 40 wt% KNO₃) is priced at the
mid-scale industrial level (~100–150 tonnes):

| Component | Wt% | Bulk Price [USD/kg] |
|-----------|-----|---------------------|
| NaNO₃ (sodium nitrate, industrial grade) | 60% | 0.40–0.60 |
| KNO₃ (potassium nitrate, industrial grade) | 40% | 0.70–1.10 |
| **Solar Salt pre-mix** | 100% | **0.90–1.50** |

**Design value: $1.00/kg** → **$144,000 USD total HTF cost**.

CSP-scale purchases (>1000 t) achieve $0.50–0.90/kg [@NREL_Gen3], while
laboratory-scale purchases exceed $2.00/kg. The sodium nitrate component
benefits from Chilean domestic production (SQM, Cosayach caliche mining).

### 4.3 Density for Mass Calculation

The `htf_density_for_mass` parameter (1900 kg/m³ in the current config) is
revised to **1875 kg/m³**, representing a temperature-averaged value across the
operating range (300–600 °C) based on CoolProp property calls for INCOMP::NaK.

---

## 5. Heat Exchanger Costs

### 5.1 Shell-and-Tube HX Cost Correlation

The purchase cost of shell-and-tube heat exchangers follows the Turton et al.
(2018) correlation [@Turton2018]:

$$\log_{10}(C_p^0) = K_1 + K_2 \cdot \log_{10}(A) + K_3 \cdot [\log_{10}(A)]^2$$

$$C_{\text{BM}} = C_p^0 \cdot (B_1 + B_2 \cdot F_M \cdot F_P)$$

where:

| Parameter | Value (floating-head) | Description |
|-----------|----------------------|-------------|
| $K_1, K_2, K_3$ | 4.8306, −0.8509, 0.3187 | Correlation coefficients |
| $A$ | variable | Heat transfer area [m²] (range: 10–1000) |
| $C_p^0$ | — | Base purchase cost (CEPCI = 500) |
| $B_1, B_2$ | 1.63, 1.66 | Bare module factors |
| $F_M$ | 3.00 | Material factor (SS316/SS316) |
| $F_P$ | 1.15 | Pressure factor (≈10 bar) |

**CEPCI escalation to 2025:**

$$C_{\text{BM, 2025}} = C_{\text{BM}} \cdot \frac{\text{CEPCI}_{2025}}{\text{CEPCI}_{\text{base}}} = C_{\text{BM}} \cdot \frac{800}{500}$$

### 5.2 Material Factor Justification

SS316 (A240-316) is required for both shell and tube sides due to molten
nitrate salt compatibility at 550–600 °C [@Bradshaw2002]. The Turton $F_M = 3.0$
for SS316/SS316 versus carbon steel (F_M = 1.0). Carbon steel is unsuitable
above ~425 °C in nitrate salt service.

### 5.3 Charge and Discharge Heat Exchangers

For the Parallel/Indirect configuration, two salt-to-salt HXs are required:

| HX | Duty [kW] | $\Delta T_{\text{lm}}$ [K] | $U$ [W/m²K] | Area [m²] | **Installed Cost [USD]** |
|----|-----------|---------------------------|-------------|-----------|--------------------------|
| Charge HX | ~500 | ~40 | 700 | 18 | **~217,000** |
| Discharge HX | ~500 | ~40 | 700 | 18 | **~217,000** |

The area is computed as $A = UA / U$ where $UA = \dot{Q} / \Delta T_{\text{lm}}$.
The overall HTC $U \approx 700$ W/m²K is typical for salt-to-salt shell-and-tube
HXs [@Turchi2013].

### 5.4 Process Heat Exchanger — Immersed Coil for Zinc Bath

For the zinc galvanizing pool, an **immersed SS316 helical coil** is used
rather than an external shell-and-tube HX with zinc circulation pump. This
follows standard industrial galvanizing practice where gas-fired tube heaters
are immersed directly in the bath [@zinc_pool_methodology].

| Parameter | Value |
|-----------|-------|
| Duty | 450 kW |
| Hot side | Solar Salt at ~520 °C |
| Cold side | Molten zinc at ~450 °C |
| $\Delta T_{\text{lm}}$ | ~40 K |
| $U$ (salt-in-tube, natural convection zinc) | ~400 W/m²K |
| Estimated area | ~30 m² |
| **Installed cost** | **~$150,000 USD** |

This configuration eliminates the need for a zinc circulation pump (highly
specialised, ~$40,000–80,000) and external zinc piping with freeze-risk trace
heating, making it ~60% cheaper than the external HX alternative. The Turton
helical coil correlation was used for base cost, with a custom fabrication
premium for the immersed geometry.

---

## 6. Pump Costs

### 6.1 Correlation

The installed cost of molten-salt centrifugal pumps follows the Turton et al.
(2018) centrifugal pump correlation [@Turton2018], with additional CSP-specific
factors for high-temperature molten salt service [@Turchi2013; @Kurup2015]:

$$C_{\text{pump}} = C_p^0(W) \cdot F_{\text{BM,SS}} \cdot F_{\text{MS}} + C_{\text{motor}}(W) + C_{\text{VFD}}(W)$$

where:

$$\log_{10}(C_p^0) = 3.3892 + 0.0536 \cdot \log_{10}(W) + 0.1538 \cdot [\log_{10}(W)]^2$$

| Factor | Value | Description |
|--------|-------|-------------|
| $C_p^0$ | — | Base purchase cost, CEPCI = 500, carbon steel |
| $F_{\text{BM,SS}}$ | 5.5 | Bare module factor for stainless steel |
| $F_{\text{MS}}$ | 1.4 | Molten salt service premium (Hastelloy wetted parts, high-T seals, thermal barrier) |
| $C_{\text{motor}}$ | Turton motor correlation | TEFC, 1800 rpm |
| $C_{\text{VFD}}$ | $250 \cdot W$ | Variable frequency drive |

**Simplified engineering fit (R² > 0.98, valid 5–50 kW):**

$$C_{\text{pump, installed}} \,[\text{USD}] = 10,800 \cdot W^{0.62}$$

### 6.2 Pump Count by Topology

| Topology | Number of Pumps | Typical Total Pump Power [kW] | **Estimated Pump CAPEX [USD]** |
|----------|----------------|------------------------------|-------------------------------|
| Parallel/Indirect | 3 (primary + secondary charge + secondary discharge/process) | 15–30 | **192,000** |
| Series/Direct | 1 (single loop) | 10–20 | **85,000** |

The Parallel/Direct configuration uses the same pump layout as Parallel/Indirect
(split flow with return merging). Series/Indirect uses 2 pumps (primary +
secondary).

---

## 7. Piping, Valves, and Instrumentation

Piping cost is estimated as a **fraction of total direct equipment cost**,
following established chemical and power plant cost estimation practice
[@Peters2004]:

$$C_{\text{piping}} = f_{\text{pipe}} \cdot \sum C_{\text{equipment}}$$

where $f_{\text{pipe}} = 0.10$ (10%). This is consistent with:

| Source | Piping Fraction | Context |
|--------|:---------------:|---------|
| Peters, Timmerhaus & West (2004) | 10–15% | General chemical plants |
| Kurup & Turchi (2015) | 5–8% | CSP parabolic trough fields |
| IRENA (2020) | 4–8% | General CSP |
| **This work** | **10%** | Molten salt with SS piping + heat tracing |

Molten salt piping uses Schedule 40/80 stainless steel with electrical heat
tracing to prevent freeze-up, commanding a higher unit cost than standard
process plant piping. The 10% value is at the upper end of the CSP range to
account for the small plant scale and salt service.

---

## 8. Engineering, Procurement, Construction (EPC) Overhead

The total direct equipment cost $C_{\text{direct}}$ is the sum of all component
installed costs (PTC, tank, HTF, HXs, pumps, piping). EPC overhead is applied
as a multiplier:

$$C_{\text{EPC}} = f_{\text{EPC}} \cdot C_{\text{direct}}$$

where $f_{\text{EPC}} = 0.25$ (25%), covering engineering design, procurement
management, construction management, commissioning, and contingency. This is
the standard factor for small-to-medium chemical process plants
[@Turton2018, Ch. 7].

---

## 9. Energy Prices (Chile)

### 9.1 Natural Gas

Chile imports nearly 100% of its natural gas as LNG via the Quintero
regasification terminal (~100 km from Santiago). Industrial prices as of
September 2025 [@GlobalPetrolPrices2025]:

| Metric | Value |
|--------|-------|
| Industrial price | **CLP 51.4/kWh = $0.056/kWh_th** |
| Equivalent thermal price | **$16.40/MMBTU** |

The auxiliary heater in the simulation burns natural gas. The energy content
conversion used is: $1 \text{ kWh_th} = 3600 \text{ kJ}$.

### 9.2 Electricity

Chilean industrial electricity prices for the central interconnected grid (SEN)
as of 2025 [@GlobalPetrolPrices2025]:

| Metric | Value |
|--------|-------|
| Spot price (Sept 2025) | **$0.200/kWh** |
| 3-year average (2023–2026) | **$0.166/kWh** |

**Design value: $0.17/kWh**, representing the 3-year average rounded.

Chile's grid CO₂ intensity is approximately 270 gCO₂/kWh (2024), declining
at ~7%/yr due to rapid solar PV deployment and coal phase-out [@Ember2025].

### 9.3 Chile Green Tax

Chile imposes a carbon tax of **$5/tonne CO₂** [@ChileGreenTax]. For a natural
gas auxiliary heater emission factor of ~0.20 kgCO₂/kWh_th, the carbon tax
contribution is approximately $0.001/kWh_th, which is negligible and absorbed
in the overall fuel price uncertainty.

---

## 10. Levelized Cost of Heat (LCOH)

### 10.1 Definition

$$\text{LCOH} \,[\text{USD/MWh}] = \frac{C_{\text{annualized}} + C_{\text{O\&M}} + C_{\text{fuel}} + C_{\text{electricity}}}{E_{\text{delivered}} \,[\text{MWh}]}$$

where:

$$C_{\text{annualized}} = C_{\text{total}} \cdot \frac{r \cdot (1+r)^n}{(1+r)^n - 1}$$

| Parameter | Value | Description |
|-----------|-------|-------------|
| $r$ | 0.08 (8%) | Discount rate [@IRENA2020] |
| $n$ | 25 years | Plant economic lifetime |
| $C_{\text{O\&M}}$ | $0.02 \cdot C_{\text{total}}$ | Annual O&M cost |
| $C_{\text{fuel}}$ | Natural gas consumed × price | Auxiliary heater fuel |
| $C_{\text{electricity}}$ | Pump electricity consumed × price | Grid electricity for pumps |
| $E_{\text{delivered}}$ | From simulation results | Total heat delivered to zinc pool |

### 10.2 Sensitivity Parameters

The LCOH is evaluated across the following sensitivity grid (implemented in
`scripts/run_economic_sensitivity.py`):

| Parameter | Base Value | Sensitivity Range |
|-----------|-----------|-------------------|
| Discount rate | 8% | 5, 8, 10, 12% |
| Plant lifetime | 25 years | 20, 25, 30 |
| Electricity price | $0.17/kWh | 0.10, 0.17, 0.25 |
| Natural gas price | $0.06/kWh_th | 0.03, 0.06, 0.09 |
| PTC specific cost | $300/m² at 1000 m² | ±30% |
| Tank specific cost | $37/kWh_th | ±30% |
| HTF price | $1.00/kg | 0.70, 1.00, 1.50 |

---

## 11. Exergoeconomic Assessment

The exergoeconomic analysis extends the economic assessment by evaluating
exergy flows and their specific costs. The methodology follows the SPECO
(Specific Exergy Costing) approach [@Lazzaretto2006], adapted to the plant
level for this work.

### 11.1 Exergy of Solar Radiation (Petela Theorem)

$$\dot{E}x_{\text{solar}} = A_{\text{ptc}} \cdot \text{DNI} \cdot \left[1 - \frac{4}{3}\left(\frac{T_0}{T_{\text{sun}}}\right) + \frac{1}{3}\left(\frac{T_0}{T_{\text{sun}}}\right)^4\right]$$

where $T_{\text{sun}} = 5770$ K and $T_0$ is the hourly ambient temperature in Kelvin.

### 11.2 Exergy of Product (Zinc Pool)

$$\dot{E}x_{\text{product}} = \dot{Q}_{\text{delivered}} \cdot \left(1 - \frac{T_0}{T_{\text{zinc}}}\right)$$

### 11.3 Plant Exergy Efficiency

$$\eta_{\text{ex}} = \frac{\sum \dot{E}x_{\text{product}} \cdot \Delta t}{\sum (\dot{E}x_{\text{solar}} + \dot{E}x_{\text{aux}}) \cdot \Delta t}$$

### 11.4 Exergoeconomic Cost Balance

$$c_P \cdot Ex_P = c_F \cdot Ex_F + \dot{Z}$$

where $c_F = 0$ for solar exergy (free), and $\dot{Z}$ is the annualised
CAPEX + O&M cost rate. The unit cost of exergy product $c_P$ is reported in
USD/MWh_ex.

---

## 12. Summary of All Economic Parameters

| Parameter | Symbol | Value | Unit | Source |
|-----------|--------|-------|------|--------|
| PTC specific cost at 1000 m² | $C_{\text{ref}}$ | 300 | USD/m² | [@Akar2025] |
| PTC economy-of-scale exponent | $n$ | 0.80 | — | [@Akar2025] |
| PTC BOP multiplier | $f_{\text{BOP}}$ | 1.40 | — | [@Turchi2013] |
| Tank vessel material | — | SS316 | — | [@Bradshaw2002] |
| Tank wall thickness (5 bar, D=7m) | $t$ | 45 | mm | [@ASME_VIII] |
| SS316 plate price | — | 5.50 | USD/kg | MEPS 2025 |
| Fill material price | — | 60 | USD/tonne | Aggregate market |
| HTF unit price (mid-scale) | — | 1.00 | USD/kg | [@NREL_Gen3] |
| HTF density (avg. 300–600 °C) | $\rho_{\text{HTF}}$ | 1875 | kg/m³ | CoolProp |
| HX correlation: floating-head SS316 | — | Turton 2018 | — | [@Turton2018] |
| HX SS316 material factor | $F_M$ | 3.00 | — | [@Turton2018] |
| HX overall U (salt-to-salt) | $U$ | 700 | W/m²K | [@Turchi2013] |
| HX overall U (salt-to-zinc coil) | $U$ | 400 | W/m²K | Estimated |
| Pump cost fit: $10,800 \cdot W^{0.62}$ | — | Turton + CSP | USD | [@Turton2018; @Turchi2013] |
| Piping fraction of direct cost | $f_{\text{pipe}}$ | 0.10 | — | [@Peters2004] |
| EPC overhead fraction | $f_{\text{EPC}}$ | 0.25 | — | [@Turton2018] |
| Discount rate | $r$ | 0.08 | — | [@IRENA2020] |
| Plant lifetime | $n$ | 25 | years | CSP standard |
| O&M fraction of CAPEX | — | 0.02 | — | CSP standard |
| Electricity price (Chile industrial) | — | 0.17 | USD/kWh | [@GlobalPetrolPrices2025] |
| Natural gas price (Chile industrial) | — | 0.06 | USD/kWh_th | [@GlobalPetrolPrices2025] |
| CEPCI (2025) | — | 800 | — | Chemical Engineering |
| Operating hours (process) | — | 3000 | h/yr | 5 d/wk × 12 h × 50 wk |
| Operating hours (standby/freeze prot.) | — | 8760 | h/yr | 24/7 |
