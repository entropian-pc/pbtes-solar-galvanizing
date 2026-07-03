# Physical Modeling, Governing Equations & Thermodynamic Coupling Methodology

This document provides a highly detailed, authoritative mathematical and physical reference for the four plant configurations and their respective operating modes in the packed bed thermal energy storage (PBTES) solar thermal plant. It serves as the primary scientific foundation for the journal publication, explaining the exact thermodynamic sizing, parameter coupling, and offdesign convergence strategies implemented in the simulation codebase.

---

## 1. System-Wide Fluid & Dynamic Load Physics

### 1.1 Heat Transfer Fluid: Solar Salt
The primary Heat Transfer Fluid (HTF) is Solar Salt (commercial molten sodium-potassium nitrate salt), represented as `INCOMP::NaK` via the CoolProp library. Solar Salt is chosen for its widespread commercial use, cost-effectiveness, and thermal stability in high-temperature applications:
* **Operating Range**: Liquid phase up to $600^\circ\text{C}$. The simulation clamps the primary working range between $300^\circ\text{C}$ and $600^\circ\text{C}$ to prevent freezing/crystallization and thermal degradation.
* **Density ($\rho$)**: Highly temperature-dependent, varying from $\sim 1900\text{ kg/m}^3$ at $300^\circ\text{C}$ to $\sim 1700\text{ kg/m}^3$ at $600^\circ\text{C}$ (modeled via the database properties of `INCOMP::NaK`). This requires transient volume-expansion modeling during charging/discharging.
* **Specific Heat ($c_p$)**: Sized in the range of 1500 J/(kg·K).
* **Thermal Conductivity ($k$)**: Standard molten salt conductivity (~0.53 W/(m·K)).

### 1.2 The Dynamic Zinc Galvanizing Bath (Process Load)
The plant serves an industrial zinc galvanizing bath, which is modeled as a dynamic lumped-capacitance thermal system. Unlike standard static process heat demands, the load is highly transient and depends on the operating schedule:
* **Operating Schedule**: Production occurs from **8:00 AM to 8:00 PM (12 hours/day), Monday through Friday**. Over weekends and nights, the bath is kept in a hot-standby state at a reduced steel load or zero throughput.
* **Governing Thermal Balance**:
  $$\left(m_{\text{Zn}} \cdot c_{p,\text{Zn}}\right) \frac{dT_{\text{Zn}}}{dt} = \dot{Q}_{\text{in}} - \dot{Q}_{\text{losses}} - \dot{Q}_{\text{production}}$$
* **Zinc Mass ($m_{\text{Zn}}$)**: $150,000\text{ kg}$ of molten zinc at a nominal operating temperature of $450^\circ\text{C}$ ($c_{p,\text{Zn}} = 512\text{ J/(kg}\cdot\text{K)}$).
* **Thermal Losses ($\dot{Q}_{\text{losses}}$)**: High natural convection and radiation losses from the molten bath surface, modeled using an overall loss coefficient:
  $$\dot{Q}_{\text{losses}} = (UA)_{\text{loss}} \left(T_{\text{Zn}} - T_{\text{amb}}\right)$$
  where $(UA)_{\text{loss}} = 500\text{ W/K}$ and $T_{\text{amb}}$ is the hourly ambient dry-bulb temperature from the TMY weather file.
* **Production Load ($\dot{Q}_{\text{production}}$)**: Heat required to raise the incoming steel throughput from ambient temperature to the galvanizing bath temperature:
  $$\dot{Q}_{\text{production}} = \dot{m}_{\text{steel}} \cdot c_{p,\text{steel}} \left(T_{\text{Zn}} - T_{\text{steel,in}}\right)$$
  where $\dot{m}_{\text{steel}} = 5,000\text{ kg/h}$ during active hours ($0\text{ kg/h}$ during standby), $T_{\text{steel,in}} = 25^\circ\text{C}$, and $c_{p,\text{steel}} = 460\text{ J/(kg}\cdot\text{K)}$.
* **Process HX Coupling**: The heat transfer from the primary HTF loop to the zinc bath is mediated by the Process Heat Exchanger (`Process_HX`), which delivers a design heat rate of $450\text{ kW}$ under full production load. The primary loop return temperature is constrained to $480^\circ\text{C}$, and the process inlet temperature is maintained at $520^\circ\text{C}$.

---

## 2. Parabolic Trough Collector (PTC) Solar Field Physics

The solar field converts Direct Normal Irradiance ($DNI$) into thermal energy. The net thermal power output ($\dot{Q}_{\text{ptc}}$) delivered to the HTF is calculated as:
$$\dot{Q}_{\text{ptc}} = A_{\text{ptc}} \cdot \left[ E \cdot \eta_{\text{opt}} \cdot K(\theta) - \dot{q}_{\text{losses}} \right]$$
where:
* **$A_{\text{ptc}}$**: Total collector aperture area ($1000\text{ m}^2$ baseline).
* **$E$**: Direct Normal Irradiance ($DNI$) from the TMY weather data.
* **$\eta_{\text{opt}}$**: Design-point optical efficiency ($0.816$), representing clean mirror reflectivity, receiver glass envelope transmissivity, and absorber tube absorptivity.
* **$K(\theta)$**: Incident Angle Modifier (IAM), accounting for optical degradation at non-normal sun angles:
  $$K(\theta) = 1 + \text{iam}_1 \cdot \theta + \text{iam}_2 \cdot \theta^2$$
  with $\text{iam}_1 = -1.59 \times 10^{-3}\text{ deg}^{-1}$ and $\text{iam}_2 = 9.77 \times 10^{-5}\text{ deg}^{-2}$, where $\theta$ is the solar incidence angle.
* **$\dot{q}_{\text{losses}}$**: Area-specific thermal heat losses from the receiver tube to the surroundings via radiation and convection:
  $$\dot{q}_{\text{losses}} = c_1 \left(T_{\text{ptc,avg}} - T_{\text{amb}}\right) + c_2 \left(T_{\text{ptc,avg}} - T_{\text{amb}}\right)^2$$
  with coefficients $c_1 = 0.0622\text{ W/(m}^2\cdot\text{K)}$ and $c_2 = 0.00023\text{ W/(m}^2\cdot\text{K}^2)$, and $T_{\text{ptc,avg}} = \frac{T_{\text{ptc,in}} + T_{\text{ptc,out}}}{2}$.

---

## 3. Packed Bed TES Physics: 1D Single-Phase Dispersion Model

The thermal energy storage (TES) tank consists of a packed bed of solid rock or ceramic pebbles ($d_p = 50\text{ mm}$, void fraction $\varepsilon = 0.40$, solid density $\rho_s = 3500\text{ kg/m}^3$, and specific heat $c_{p,s} = 968\text{ J/(kg}\cdot\text{K)}$). The bed is modeled as a pseudo-homogeneous medium with a single temperature field $T(z, t)$, under the assumption of local thermal equilibrium between the fluid and solid phases. This single-phase dispersion formulation retains axial thermal dispersion and wall heat transfer while reducing the classical two-phase Schumann equations to a single energy equation, yielding a computationally efficient analytical eigenvalue solution without numerical diffusion.

```
                   Top Node (z = 0)  — T_top
                 ┌───────────────────┐
                 │                   │  ▲  Discharging
  Charging       │    Packed Bed     │  │  (Flow: bottom to top)
  (Flow: top     │                   │  │  T_out_dis = T_top
  to bottom)     │    Thermocline    │  │
  T_out_ch       │     Gradient      │  │
  = T_bottom     │                   │  │
  ▼              └───────────────────┘
                  Bottom Node (z = H) — T_bottom
```

### 3.1 Governing Equation
The energy balance for the packed bed is expressed as a one-dimensional advection–dispersion equation with a wall heat transfer term:

$$\rho_{cp,eff} \frac{\partial T}{\partial t} + \varepsilon \rho_f c_{p,f} \, u_{in} \frac{\partial T}{\partial z} = k_{eff} \frac{\partial^2 T}{\partial z^2} - h_w \, \beta \, (T - T_{ref})$$

where the effective volumetric heat capacity combines the fluid and solid contributions:

$$\rho_{cp,eff} = \varepsilon \rho_f c_{p,f} + (1 - \varepsilon) \rho_s c_{p,s}$$

The advective term is weighted by the fluid capacitance fraction $\kappa = \varepsilon \rho_f c_{p,f} / \rho_{cp,eff}$, reflecting that only the fluid phase transports energy axially while both phases store heat. The interstitial velocity is $u_{in} = G / \rho_f$, where $G = \dot{m} / A_{\text{bed}}$ is the mass flux per unit cross-sectional area. The wall surface-to-volume ratio is $\beta = 4/D$ for a cylindrical tank.

**Effective thermal conductivity.** The axial effective conductivity combines a volume-weighted average and a flow-dependent dispersion term:

$$k_{eff} = \underbrace{\varepsilon k_f + (1 - \varepsilon) k_s}_{k_{line}} + \frac{\left[(1 - \varepsilon) \rho_s c_{p,s} \cdot \frac{G \, c_{p,f}}{\rho_{cp,eff}}\right]^2}{h_v}$$

The dispersion contribution scales with the square of the mass flux and vanishes at zero flow, reducing $k_{eff}$ to the stagnant conductivity $k_{line}$. [adapted from prior work — source pending Felipe review]

**Volumetric heat transfer coefficient.** The particle-to-fluid surface heat transfer coefficient $h_{sf}$ is obtained from the Wakao–Kaguei correlation \cite{Wakao1979}:

$$Nu = \frac{h_{sf} \, d_p}{k_f} = 2.0 + 1.1 \, Re^{0.6} Pr^{1/3}$$

valid for $15 \le Re \le 8500$ and $0.6 \le Pr \le 160$. The conduction asymptote ($Nu \to 2.0$ as $Re \to 0$) ensures finite heat transfer at the low Reynolds numbers characteristic of molten salt flow ($Re < 15$ in this study). The volumetric heat transfer coefficient is:

$$h_v = \frac{6(1 - \varepsilon)}{d_p} h_{sf}$$

where the factor $6(1-\varepsilon)/d_p$ is the specific surface area of the packed bed.

**Wall heat transfer.** The internal wall heat transfer coefficient is computed from a two-term Nusselt-type correlation:

$$Nu_w = \frac{h_w \, d_p}{k_f} = 0.203 \, Re^{1/3} Pr^{1/3} + 0.22 \, Re^{0.8} Pr^{0.4}$$

The first term represents the low-Reynolds contribution with $Re^{1/3}$ scaling, and the second term represents the forced-convective contribution. [FLAG: no literature source identified for this correlation — adapted from prior work, source pending Felipe review; see §F3 in `context/parameter_validation_report.md`] The wall heat transfer enters the governing equation through a Stanton number:

$$St = \frac{0.75 \, h_w \, \beta \, H}{\rho_{cp,eff} \, u_{in}}$$

where the factor 0.75 is an empirical multiplier. [FLAG: physical basis of the 0.75 multiplier undocumented — pending Felipe review]

Wall heat loss through the tank insulation to ambient during standby periods is modeled separately via a cylindrical resistance network and is described in §7.

### 3.2 Analytical Eigenvalue Solution
The spatial domain is normalized as $x = z/H \in [0, 1]$ with 20 structural nodes, and the dimensionless time step is $\tau = u_{in} \Delta t / H$. Introducing the Péclet number $Pe = u_{in} H / \alpha_{eff}$, where $\alpha_{eff} = k_{eff} / \rho_{cp,eff}$, and the capacitance fraction $\kappa = \varepsilon \rho_f c_{p,f} / \rho_{cp,eff}$, the governing equation in dimensionless form reads:

$$\frac{\partial \theta}{\partial \tau} = \frac{1}{Pe} \frac{\partial^2 \theta}{\partial x^2} - \kappa \frac{\partial \theta}{\partial x} - St \cdot \theta$$

The parameter $a = \kappa Pe / 2$ is clipped to $|a| \le 15.0$ to prevent overflow in the exponential functions of the analytical solution. When clipping is invoked, $Pe$ is recomputed from the clipped $a$ to maintain consistency.

The solution is decomposed into a stationary part $\theta_s(x)$ and a transient part $\theta_t(x, \tau)$, such that $\theta(x, \tau) = \theta_s(x) + \theta_t(x, \tau)$.

**Stationary solution.** Setting $\partial \theta / \partial \tau = 0$ yields a second-order ODE whose characteristic equation $k^2 - \kappa Pe \, k - Pe \, St = 0$ has roots:

$$k_{1,2} = \frac{1}{2}\left(\kappa Pe \pm \sqrt{\kappa^2 Pe^2 + 4 Pe \, St}\right)$$

The stationary profile is:

$$\theta_s(x) = C_1 e^{k_1 x} + C_2 e^{k_2 x}$$

where the constants $C_1$ and $C_2$ are determined from the normalized inlet temperature $\theta_{in} = (T_{in} - T_{min})/(T_{max} - T_{min})$ and the boundary condition at $x = 1$.

**Transient solution.** The substitution $\phi = (\theta - \theta_s) \, e^{-ax}$ eliminates the first-order advection term, reducing the problem to a diffusion equation with a decay source. Separation of variables yields eigenfunctions $\sin(\lambda_n x)$ with eigenvalues $\lambda_n$ satisfying the transcendental equation:

$$\frac{\lambda_n}{a} + \tan(\lambda_n) = 0$$

A total of 200 eigenvalues are computed using Brent's method \cite{brentq}, with each root bracketed in an interval of width $\pi/2$. The transient solution is:

$$\theta_t(x, \tau) = e^{ax + b\tau} \sum_{n=1}^{200} A_n \, f_n \, \sin(\lambda_n x) \, \exp\!\left(-\frac{\lambda_n^2 \tau}{Pe}\right)$$

where $b = -(St + a^2/Pe)$, the normalization factors are $f_n = \sqrt{2}\,\sqrt{(\lambda_n^2 + a^2)/(\lambda_n^2 + a^2 + a)}$, and the expansion coefficients $A_n$ are obtained by projecting the initial condition (interpolated from the 20-node profile onto a 200-point integration grid) onto the eigenfunction basis via trapezoidal integration.

The full solution is evaluated at the 20 spatial nodes and rescaled to physical temperature:

$$T = \theta \, (T_{max} - T_{min}) + T_{min}$$

where $T_{min}$ and $T_{max}$ are the extrema of the current profile and inlet temperature. This analytical approach preserves the thermocline gradient without the numerical diffusion inherent in finite-difference schemes.

**Charge–discharge reversal.** The bed is charged with flow from top to bottom and discharged with flow from bottom to top. The profile array is reversed upon each state transition, maintaining the inlet at $x = 0$ in the solution coordinate.

### 3.3 State of Charge (SoC) Calculation
The state of charge is computed as the absolute sensible energy stored in the bed above a reference temperature $T_{ref} = 300^\circ\text{C}$:

$$SoC = \frac{V_{\text{bed}} \; \overline{C}_{vol} \; \overline{(T - T_{ref})}}{3.6 \times 10^6} \quad [\text{kWh}]$$

where $V_{\text{bed}} = \pi (D/2)^2 H$ is the bed volume, $\overline{C}_{vol} = (1 - \varepsilon)\rho_s c_{p,s} + \varepsilon \bar{\rho}_f \bar{c}_{p,f}$ is the volumetric heat capacity evaluated at the mean profile temperature, and $\overline{(T - T_{ref})}$ is the mean temperature excess above the reference. The fluid properties $\bar{\rho}_f$ and $\bar{c}_{p,f}$ are evaluated via CoolProp at the average bed temperature. This mean-property approximation introduces a $\sim$2–3\% error relative to per-node integration, attributable to the Solar Salt density variation of $1900 \to 1700\text{ kg/m}^3$ over the $300$–$600^\circ\text{C}$ operating range; the error is acceptable for system-level analysis.

---

## 4. Configuration Physics & Thermodynamic Coupling

The 2×2 configuration matrix determines the flow routing, energy exchange boundaries, and mathematical constraints solved by TESPy and the 1D Schumann model.

```
                  2×2 CONFIGURATION MATRIX
              
                         INDIRECT                           DIRECT
            ┌─────────────────────────────────┐┌─────────────────────────────────┐
            │ • Split flow post-PTC.          ││ • Split flow post-PTC.          │
            │ • Charging HX + Discharging HX  ││ • Hot Tank on solar branch;     │
            │   decouple loops.               ││   Cold Tank on process return.  │
  PARALLEL  │ • Mode 5 High-T HX in parallel. ││ • Mode 3 analytical mixing via  │
            │ • Mode 6 decoupled cycles (x3   ││   parallel tank discharge.      │
            │   pumps).                       ││ • Mode 5 HT-charging of Hot Tank│
            └─────────────────────────────────┘└─────────────────────────────────┘
            ┌─────────────────────────────────┐┌─────────────────────────────────┐
            │ • Single loop: PTC → Process    ││ • Single loop: PTC → Hot Tank   │
            │   → Charging HX → PTC.          ││   → Process → Cold Tank → PTC.  │
   SERIES   │ • TES charges at process return ││ • Both tanks directly in loop.  │
            │   temperature (~480°C).         ││ • Adaptive auxiliary heating for│
            │ • Separate discharge loop.      ││   cold-tank startup.            │
            └─────────────────────────────────┘└─────────────────────────────────┘
```

---

### 4.1 Parallel Indirect (PI) Configuration

The baseline Parallel Indirect configuration splits the primary loop into process and charging branches. The TES operates in a secondary loop, thermally decoupled by high-effectiveness heat exchangers.

```
  Primary Loop (Mode 1 split flow)
  
                  ┌──► [Preheater HX] ──► [Process HX] ──┐
  [PTC Field] ──►┤                                       ├──► [Primary Pump] ──┐
                  └──► [Charge HX: Hot Side] ────────────┘                     │
                             ▲                                                 │
                             │ (Heat transfer)                                 │
                             ▼                                                 │
  TES Secondary Loop         │                                                 │
                             │                                                 │
  [Secondary Pump] ──► [Charge HX: Cold Side] ──► [PBTES Bed] ─────────────────┘
```

#### 4.1.1 Governing Design Sizing Equations
In design mode, the primary split ratio, HX conductance, and mass flows are sized simultaneously to deliver process heat and charge the storage at the design irradiance ($900\text{ W/m}^2$):
1. **Solar Splitting Balance**:
   $$\dot{m}_{\text{ptc}} = \dot{m}_{\text{proc}} + \dot{m}_{\text{charge,primary}}$$
2. **Process Heat Duty**:
   $$\dot{Q}_{\text{proc}} = \dot{m}_{\text{proc}} \cdot c_{p,\text{HTF}} \left(T_5 - T_6\right) = 450\text{ kW}$$
   where $T_5 = 520^\circ\text{C}$ and $T_6 = 480^\circ\text{C}$ are fixed boundary constraints.
3. **TES Sizing (Logarithmic Mean Temperature Difference)**:
   The sizing of the `Charge_TES_HX` is governed by the terminal temperature difference constraint ($ttd_l = 20.0\text{ K}$):
   $$ttd_l = T_{\text{hot,out}} - T_{\text{cold,in}} = T_{10} - T_{13}$$
   where $T_{10}$ is the primary return temperature on the charging branch and $T_{13}$ is the cold storage temperature. The heat transfer rate determines the designed conductance ($kA_{\text{charge}}$):
   $$\dot{Q}_{\text{charge}} = (kA)_{\text{charge}} \cdot \Delta T_{\text{lm,charge}}$$
   $$\Delta T_{\text{lm,charge}} = \frac{\left(T_{\text{ptc,out}} - T_{14}\right) - \left(T_{10} - T_{13}\right)}{\ln\left(\frac{T_{\text{ptc,out}} - T_{14}}{T_{10} - T_{13}}\right)}$$
   where $T_{14}$ is the hot secondary fluid entering the top of the PBTES bed.

#### 4.1.2 Offdesign & Thermodynamic Coupling Loop
During transient simulation, the structural conductance $kA$ remains constant. To avoid over-constraining the offdesign network, variables such as primary flow split and temperatures are solved using the steady-state solver with the following coupling loop:
1. **Initialize Guess**: Guess the PBTES outlet temperature $T_{13}^0 = T_s(z=H, t)$ (bottom of bed).
2. **TESPy Network Solution**: Solve the offdesign network using the fixed $(kA)_{\text{charge}}$:
   - Primary mass flow rate $\dot{m}_{\text{ptc}}$ and split fraction are calculated by the solver.
   - Secondary loop mass flow $\dot{m}_{\text{sec}}$ is matched to the primary charging branch capacity to maintain heat capacity ratio stability.
   - PBTES inlet temperature $T_{14}$ is returned.
3. **Schumann Model Integration**: Solve the 1D Schumann model for the secondary charging fluid flow:
   $$T_{13}^{\text{new}} = \text{Schumann\_Step}\left(T_{14}, \dot{m}_{\text{sec}}, \Delta t\right)$$
4. **Convergence Check**: Repeat steps 2-3 until $|T_{13}^{\text{new}} - T_{13}^0| < 10^{-3}\text{ K}$.
5. **Mode 3 Discharging Coupling**: In offdesign discharging, the process side temperature is set via a coupling target: $T_4 = T_{15} - 20\text{ K}$, where $T_{15}$ is the hot outlet of the PBTES (top of bed). The secondary discharge mass flow is propagated from the designed sizing value, and the preheater heat duty $Q_{\text{aux}}$ is governed by two continuous operating regimes:
   * **Regime A (Preheater $Q_{\text{aux}} = 0$)**: Triggered when $T_{15} \ge 540^\circ\text{C}$ (i.e. $T_{\text{target}} + 20\text{ K}$ to account for the design heat exchanger temperature drop). The process inlet temperature $T_5$ floats freely above the target ($T_5 = T_4 \ge 520^\circ\text{C}$).
   * **Regime B (Preheater $Q_{\text{aux}} > 0$)**: Triggered when $T_{15} < 540^\circ\text{C}$. The preheater actively tops up the process inlet to exactly $520^\circ\text{C}$ ($T_5 = 520^\circ\text{C}$ is fixed and $Q_{\text{aux}} = \text{'var'}$).
   * This refined regime boundary prevents physical and mathematical step-change discontinuities (which would occur if switching at $520^\circ\text{C}$). Discharging is viable down to a state-of-charge floor of $SoC > 2\%$ ($soc\_norm > 0.02$) and $T_{15} > 500^\circ\text{C}$.

---

### 4.2 Series Direct (SD) Configuration

The Series Direct configuration routes the HTF through all components sequentially, eliminating coupling HXs and the secondary loop pump. The packed bed storage is divided into two stratified vessels: the **Hot Tank** and the **Cold Tank**.

```
  Primary Loop (Mode 1 charging)
  
  [PTC Field] ──► [Hot Tank (Direct Bed)] ──► [Preheater HX (Q=0)] ──► [Process HX] ──┐
                                                                                     │
  [Primary Pump] ◄── [Cold Tank (Direct Bed)] ◄──────────────────────────────────────┘
```

#### 4.2.1 Direct-Contact Modeling in TESPy
The Hot and Cold tanks are represented inside the TESPy network as `SimpleHeatExchanger` components (`hot_tank_hx` and `cold_tank_hx`). Unlike full heat exchangers, these represent a direct single-phase pressure drop and enthalpy change as the Solar Salt passes through the rock bed. The coupling variables are the outlet temperatures, set as primary connection boundary conditions:
* **Hot Tank Outlet**: $\text{conn\_ht\_ph.T} = T_{\text{hot,out}}$ (bottom of the Hot Tank bed)
* **Cold Tank Outlet**: $\text{conn\_10.T} = T_{\text{cold,out}}$ (bottom of the Cold Tank bed)

#### 4.2.2 The Cold-Tank Thermodynamic "Lockup" & Auxiliary Preheater Fix
A major physical challenge arises when the Hot and Cold tanks are cold (e.g., initialized at low temperatures or depleted during long discharge periods). 
* **The Physics of Lockup**: During Mode 1 charging, the HTF must flow from the PTC, through the Hot Tank, and then into the process. If the Hot Tank is depleted, its outlet temperature $T_{\text{hot,out}}$ (bottom node) drops to around $300^\circ\text{C}$. If the Preheater is constrained to `Q=0` (solar-only), the fluid enters the Process HX at $T_5 = T_{\text{hot,out}} \approx 300^\circ\text{C}$. 
* **Thermodynamic Bound Violation**: The Process HX extracts heat to serve the galvanizing bath, forcing the return temperature $T_6$ to fall dramatically below the melting/liquid limits. In CoolProp, attempting to evaluate Solar Salt properties below the physical bounds ($300.1^\circ\text{C}$) results in immediately divergent density calculations and matrix singularity failures.
* **The Adaptive Preheater Control Logic**:
  To resolve this thermodynamic lockup, an **Adaptive Auxiliary Preheater Block** is implemented in `system.py`:
  $$\begin{cases}
  \text{If } T_{\text{hot,out}} < 520.0^\circ\text{C}: & \text{Set } Q_{\text{preheater}} = \text{'var'}, \ \text{conn\_05.T} = 520.0^\circ\text{C} \\
  \text{If } T_{\text{hot,out}} \ge 520.0^\circ\text{C}: & \text{Set } Q_{\text{preheater}} = 0, \ \text{conn\_05.T} = \text{None}
  \end{cases}$$
  
  When the tank is cold, the auxiliary preheater actively tops up the fluid temperature entering the process to $520.0^\circ\text{C}$. This keeps the process return at $480.0^\circ\text{C}$, preventing the temperature crash and allowing the solar field to successfully charge the Hot Tank and Cold Tank until the bottom temperatures rise above the threshold.

#### 4.2.3 Mode 3 Discharging — Analytical Mixing (Option A)
To prevent flow-reversal and splitting matrix singularities in TESPy during discharge, the two-tank parallel discharge is solved **analytically** outside the thermodynamic network solver:

```
  Two-Tank Discharging (Mode 3)
  
  [Hot Tank (T_hot)]  ──► [ṁ_hot]  ──┐
                                     ├──► [Mixing Valve] ──► [T_mix] ──► [Process HX] ──┐
  [Cold Tank (T_cold)] ──► [ṁ_cold] ──┘                                                 │
                                                                                        │
  [Hot/Cold Tank Bottoms] ◄── [Split Return] ◄── [Primary Pump] ◄───────────────────────┘
```

1. **Temperature Blending Physics**:
   $$T_{\text{mix}} = \frac{\dot{m}_{\text{hot}} T_{\text{hot}} + \dot{m}_{\text{cold}} T_{\text{cold}}}{\dot{m}_{\text{hot}} + \dot{m}_{\text{cold}}}$$
   where $T_{\text{hot}} = T_{\text{hot\_bed}}(z=0)$ and $T_{\text{cold}} = T_{\text{cold\_bed}}(z=0)$ are the top-of-bed temperatures.
2. **Mass Flow Split Ratio ($r$)**:
   To hit the target process inlet $T_{\text{target}} = 520^\circ\text{C}$, the mass flow ratio is calculated as:
   $$r = \frac{\dot{m}_{\text{hot}}}{\dot{m}_{\text{cold}}} = \frac{T_{\text{target}} - T_{\text{cold}}}{T_{\text{hot}} - T_{\text{target}}}$$
   Using the total required process mass flow $\dot{m}_{\text{total}}$, the split flows are:
   $$\dot{m}_{\text{hot}} = \frac{r}{1+r} \dot{m}_{\text{total}}, \quad \dot{m}_{\text{cold}} = \frac{1}{1+r} \dot{m}_{\text{total}}$$
3. **Control Saturation Constraints**:
   * **Cold Preservation**: If $T_{\text{cold}} \ge 520^\circ\text{C}$, the system prioritizes discharging the Cold Tank ($r \to 0$) to preserve high-grade Hot Tank heat.
   * **Depletion / Auxiliary Shortfall**: If $T_{\text{hot}} < 520^\circ\text{C}$, the Hot Tank alone cannot meet the target. The system saturates the valve to draw exclusively from the Hot Tank ($\dot{m}_{\text{hot}} = \dot{m}_{\text{total}}$, $\dot{m}_{\text{cold}} = 0$). The mixed temperature is $T_{\text{mix}} = T_{\text{hot}}$, and the auxiliary preheater provides the remaining heating rate:
     $$\dot{Q}_{\text{aux}} = \dot{m}_{\text{total}} \cdot c_{p,\text{HTF}} \left(520^\circ\text{C} - T_{\text{hot}}\right)$$
4. **Schumann Model Updates**:
   During discharging, fluid enters the **bottom** of the tanks at the process return temperature ($480^\circ\text{C}$) and exits from the **top**. The Schumann models for both beds are updated independently using their respective analytical mass flows $\dot{m}_{\text{hot}}$ and $\dot{m}_{\text{cold}}$.

---

### 4.3 Parallel Direct (PD) Configuration

The Parallel Direct configuration combines the split-flow layout of Parallel with the direct-contact tank layout of Direct.
* **Charging Path (Mode 1)**: The primary split divides the Solar Salt leaving the PTC:
  * **TES Branch**: Hot Solar Salt at PTC outlet temperature ($\sim 560^\circ\text{C}$) flows directly into the top of the **Hot Tank**, charging it at the highest thermal potential.
  * **Process Branch**: Fluid flows through the Preheater and Process HX, delivering $450\text{ kW}$. The cooler return fluid ($\sim 480^\circ\text{C}$) flows directly into the **Cold Tank**, charging it.
  * Both branches merge after exiting the bottoms of the respective tanks and return to the primary pump.
* **Discharging Path (Mode 3)**: Solved analytically using Option A (parallel tank discharging through the mixing valve), identical to the Series Direct discharging formulation.

---

### 4.4 Series Indirect (SI) Configuration

The Series Indirect configuration routes fluid sequentially in a single loop, but uses a decoupling heat exchanger and a secondary pump for the storage loop.
* **Charging Path (Mode 1)**: Solar Salt flows sequentially: PTC $\to$ Preheater HX $\to$ Process HX $\to$ Charge HX $\to$ PTC.
  * **Thermodynamic Sizing Constraint**: Because the Charge HX is located downstream of the process, it only receives fluid *after* the process has extracted heat. This limits the maximum charging fluid temperature to the process return level ($\sim 480^\circ\text{C}$).
  * **Conductance Sizing**: The Charge HX must be sized at the lower temperature level, resulting in a larger required physical surface area ($kA$) to transfer the same thermal power compared to Parallel configurations.
* **Discharging Path (Mode 3)**: Utilizes a dedicated Discharge HX and a secondary discharge pump to transfer energy from the secondary loop to the process loop, matching the Parallel Indirect discharge equations.

---

## 5. Summary Matrix: Thermodynamic Limits & Physical Constraints

| Configuration | Solar Coupling Mode 1 | Storage Charging Temp | Pump Count (M1 / M3) | Dominant HX Sizing Constraints | Auxiliary Startup Behavior |
|---|---|---|---|---|---|
| **Parallel Indirect (PI)** | Decoupled via Charge HX; primary split flow | PTC outlet temp ($\sim 560^\circ\text{C}$) | 2 / 2 | $(kA)_{\text{charge}}$ sized at high-T branch with $ttd_l = 20\text{ K}$ | Standard preheater bypass; solar split manages charging surplus |
| **Parallel Direct (PD)** | Direct contact; primary split flow | Hot Tank: $\sim 560^\circ\text{C}$<br/>Cold Tank: $\sim 480^\circ\text{C}$ | 1 / 1 | No charging HX; bed pressure drop sized via Ergun equation | Standard solar split; direct-tank boundary iteration |
| **Series Indirect (SI)** | Decoupled via Charge HX; primary series flow | Process return temp ($\sim 480^\circ\text{C}$) | 2 / 2 | $(kA)_{\text{charge}}$ sized at return branch; larger physical area required | Preheater bypass; charging capacity limited by return temperature |
| **Series Direct (SD)** | Direct contact; primary series flow | Hot Tank: $\sim 560^\circ\text{C}$<br/>Cold Tank: $\sim 480^\circ\text{C}$ | 1 / 1 | No charging HX; Hot Tank upstream, Cold Tank downstream | **Adaptive Preheater Block** tops up process to $520^\circ\text{C}$ if $T_{\text{hot,out}} < 520^\circ\text{C}$ |

---

## 6. Pump Power & Pressure Drop Characterization (Post-Processed)

To maintain robustness and prevent solver convergence failures under highly transient density changes, the pumping power is post-processed at each timestep rather than solved inline within the TESPy matrix.

### 6.1 Pressure Drop in Pipes and Heat Exchangers
Pressure drops ($\Delta p$) across the standard steady-state heat exchangers and piping loops are modeled using quadratic flow relationships:
$$\Delta p = \alpha \cdot \dot{m}^2$$
where $\alpha$ is a structural flow coefficient sized at the design point to match nominal pressure losses.

### 6.2 Packed Bed Pressure Drop: The Ergun Equation
The pressure drop across the PBTES packed beds ($\Delta p_{\text{bed}}$) is calculated using the Ergun equation, accounting for both laminar (viscous) and turbulent (inertial) drag forces inside the stratified bed:
$$\frac{\Delta p_{\text{bed}}}{H} = 150 \frac{(1 - \varepsilon)^2}{\varepsilon^3} \frac{\mu_f \cdot u_0}{d_p^2} + 1.75 \frac{1 - \varepsilon}{\varepsilon^3} \frac{\rho_f \cdot u_0^2}{d_p}$$
where:
* **$u_0$**: Superficial velocity ($u_0 = u \cdot \varepsilon = \dot{m} / (\rho_f A_{\text{bed}})$).
* **$\mu_f$**: Dynamic viscosity of Solar Salt, updated transiently based on local temperatures.
* **$H$**: Structural height of the packed bed ($5.0\text{ m}$ baseline).

### 6.3 Pumping Power and Solar Fraction Integration
The electrical pumping power required ($W_{\text{pump}}$) is post-processed using the calculated mass flows and pressure drops across all active flow paths:
$$W_{\text{pump}} = \sum_{j} \frac{\dot{m}_j \cdot \Delta p_j}{\rho_f \cdot \eta_{\text{pump}}}$$
where $\eta_{\text{pump}} = 0.75$ is the overall combined pump and motor efficiency. The net solar fraction ($SF_{\text{net}}$) is adjusted during post-processing to account for the electrical energy consumed by the pumps, converting it to equivalent thermal losses using the plant's thermal-to-electrical conversion penalty:
$$SF_{\text{net}} = \frac{\sum \left( \dot{Q}_{\text{solar,proc}} + \dot{Q}_{\text{tes,proc}} \right) \cdot \Delta t - \frac{W_{\text{pump,total}} \cdot \Delta t}{\eta_{\text{power\_cycle}}}}{\sum \left( \dot{Q}_{\text{solar,proc}} + \dot{Q}_{\text{tes,proc}} + \dot{Q}_{\text{aux,proc}} \right) \cdot \Delta t}$$
where $\eta_{\text{power\_cycle}} = 0.35$ represents the baseline thermal power cycle efficiency.

---

## 7. Seasonal Winter Control Logic & Tank Auxiliary Heaters

To ensure the physical integrity of the plant during periods of low solar resource (Southern Hemisphere winter: June, July, and August) and prevent Solar Salt from cooling below the CoolProp property limits ($300.1^\circ\text{C}$), an active **Tank Auxiliary Heating System** and a **Winter Control Logic** are integrated.

### 7.1 Tank Heater Blanket Physical Model
The tank auxiliary heaters are modeled as electric blankets wrapped around the steel tank walls (sandwiched between the steel wall and outer insulation). 

```
          Fluid Bed Node (T)
                 │
                 ├──► [ R_wall ]
                 │
           Blanket Node (T_set)
                 │
                 ├──► [ R_ins + R_conv ]
                 │
            Ambient (T_amb)
```

For any given layer structure $i$, if the unheated timestep temperature $T_{\text{new,unheated}}$ falls below the active setpoint $T_{\text{set}}$, the blanket heater turns on to clamp the node temperature to $T_{\text{set}}$. The energy consumption is computed as the sum of:
1. **Heat delivered to the tank layer** ($\dot{Q}_{\text{to\_tank}}$), required to raise the layer from its unheated temperature to the setpoint:
   $$\dot{Q}_{\text{to\_tank}, i} = C_{\text{eff}, i} \frac{T_{\text{set}} - T_{\text{new,unheated}, i}}{\Delta t}$$
2. **Heat lost from the blanket to the environment** ($\dot{Q}_{\text{to\_env}}$), which passes through the outer insulation and convective boundary layers:
   $$\dot{Q}_{\text{to\_env}, i} = \frac{T_{\text{set}} - T_{\text{amb}}}{R_{\text{ins}, i} + R_{\text{conv}, i}}$$

The total auxiliary blanket energy consumed by structural node $i$ over the step is:
$$E_{\text{blanket}, i} = \left( \dot{Q}_{\text{to\_tank}, i} + \dot{Q}_{\text{to\_env}, i} \right) \cdot \Delta t$$

### 7.2 Winter Logic Operational Scheme
The dynamic target setpoint $T_{\text{set}}$ is governed by the seasonal `WinterLogic` controller:
* **Production Months (Sept–May)**: The storage tanks are maintained at $T_{\text{set\_production}} = 450.0^\circ\text{C}$ to keep them warm and ready for operation.
* **Winter Months (June–Aug)**: To conserve energy while preventing freeze-up, the storage setpoint is lowered to $T_{\text{set\_winter}} = 300.1^\circ\text{C}$ (freeze protection threshold).

### 7.3 Integration Across Configurations
1. **Parallel/Indirect (PI) Mode 6 Regimes**:
   In Parallel Indirect, charging the storage while the process is decoupled (Mode 6) operates under two seasonal regimes:
   - **Regime A (Winter/Standby)**: Mode 6 charges/maintains the tank at $T_{\text{set\_winter}} = 300.1^\circ\text{C}$.
   - **Regime B (Production)**: Mode 6 charges/maintains the tank at $T_{\text{set\_production}} = 450.0^\circ\text{C}$.
2. **Series/Direct (SD) Heating Modes**:
   Since the direct-contact beds are directly in the primary loop, the Hot and Cold tank blankets are active across all modes (Modes 1, 2, 3, 4) to clamp Solar Salt temperatures to the active setpoint (either $450.0^\circ\text{C}$ or $300.1^\circ\text{C}$).

---

## 8. Economic Assessment Methodology

The economic and exergoeconomic assessment of the plant follows a bottom-up
capital cost estimation approach validated against CSP and chemical process
engineering literature. The full methodology with all correlations, parameter
justifications, and literature citations is documented in the companion file
`insumos paper/ECONOMIC_METHODOLOGY.md`. This section summarises the key
equations and input values.

### 8.1 System Boundary

The economic assessment evaluates the incremental costs of integrating a solar
field and TES into an existing zinc galvanizing plant. Zinc bath infrastructure,
buildings, and existing labour are excluded. The system boundary includes: PTC
field, TES tank with fill material and insulation, Solar Salt inventory, all
heat exchangers, HTF circulation pumps, interconnecting piping, and EPC overhead.

### 8.2 PTC Field Cost

$$C_{\text{PTC}} = C_{\text{ref}} \cdot A_{\text{ptc}} \cdot \left(\frac{A_{\text{ptc}}}{A_{\text{ref}}}\right)^{n-1} \cdot f_{\text{BOP}}$$

with $C_{\text{ref}} = 300$ USD/m² at $A_{\text{ref}} = 1000$ m², $n = 0.80$,
$f_{\text{BOP}} = 1.40$, based on the NREL DFMA model [@Akar2025].

### 8.3 TES Tank Cost

The tank vessel wall thickness follows the ASME VIII-1 hoop stress formula:

$$t = \frac{P \cdot R}{\sigma_{\text{allow}} \cdot E - 0.6P} + t_{\text{corr}}$$

The vessel is SS316 (A240-316) plate, $t_{\text{design}} = 45$ mm for
D = 7.0 m at 5 bar and 600 °C. The total installed tank cost is computed
bottom-up from vessel material, multi-layer insulation, rock fill, civil works,
piping, and EPC overhead, following the methodology of Turton et al. (2018)
and Peters et al. (2004) [@Turton2018; @Peters2004].

### 8.4 Heat Exchanger Costs

Shell-and-tube HX costs follow the Turton et al. (2018) correlation
for floating-head exchangers with SS316/SS316 material factor ($F_M = 3.0$):

$$\log_{10}(C_p^0) = 4.8306 - 0.8509 \cdot \log_{10}(A) + 0.3187 \cdot [\log_{10}(A)]^2$$

$$C_{\text{BM}} = C_p^0 \cdot (1.63 + 1.66 \cdot F_M \cdot F_P) \cdot \frac{\text{CEPCI}_{2025}}{\text{CEPCI}_{\text{base}}}$$

The process HX for the zinc pool is modelled as an immersed SS316 helical
coil (U ≈ 400 W/m²K), following standard galvanizing practice.

### 8.5 Pump Costs

Molten-salt pump installed costs follow a simplified power-law fit to the
Turton et al. (2018) centrifugal pump correlation, with a CSP-specific
premium for Hastelloy wetted parts and high-temperature seals [@Turchi2013]:

$$C_{\text{pump}} = 10{,}800 \cdot W^{0.62} \quad [\text{USD, kW}]$$

### 8.6 HTF, Piping, and EPC

Solar Salt priced at $1.00/kg (mid-scale industrial, 2025). Piping at 10%
of direct equipment cost. EPC overhead at 25% of total direct cost.

### 8.7 Energy Prices

Chilean industrial electricity: $0.17/kWh; natural gas: $0.06/kWh_th,
from GlobalPetrolPrices (2025) and CNE tariff data.

### 8.8 Levelized Cost of Heat

$$\text{LCOH} = \frac{C_{\text{annualized}} + C_{\text{O\&M}} + C_{\text{fuel}} + C_{\text{electricity}}}{E_{\text{delivered}}}$$

with discount rate $r = 8\%$, plant lifetime $n = 25$ years, O&M at $2\%$
of CAPEX per year.

### 8.9 Exergoeconomic Analysis

A plant-level exergoeconomic assessment following the SPECO methodology
[@Lazzaretto2006] is applied. Solar exergy input uses the Petela theorem
($T_{\text{sun}} = 5770$ K), product exergy uses the Carnot factor at the
zinc pool temperature, and auxiliary exergy is valued at its energy content.
The unit exergoeconomic cost of product is:

$$c_P = \frac{c_F \cdot Ex_F + \dot{Z}}{Ex_P}$$

where $c_F = 0$ for solar exergy (free input).
