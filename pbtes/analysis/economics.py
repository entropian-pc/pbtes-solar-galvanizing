"""
pbtes/analysis/economics.py

Economic and Exergoeconomic assessment module for the PBTES solar thermal plant.
Calculates Levelized Cost of Heat (LCOH) with component-level CAPEX breakdown
based on validated cost correlations from CSP and chemical process literature.

References are documented in ``insumos paper/ECONOMIC_METHODOLOGY.md``
and ``insumos paper/references.bib``.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from pbtes.config import SimulationConfig


class EconomicAssessment:
    """
    Evaluates the economic performance of a PBTES plant design given
    its hourly simulation results.

    Cost correlations:
      - PTC: Akar & Kurup (2025), economy-of-scale power law + BOP factor
      - Tank: Bottom-up ASME VIII-1 vessel + insulation + fill + EPC
      - HTF: Mid-scale industrial Solar Salt pricing
      - HX: Turton et al. (2018) floating-head SS316/SS316
      - Pumps: Turton et al. (2018) + CSP molten-salt premium
      - Piping: 10% of equipment subtotal (Peters & Timmerhaus, 2004)
      - EPC overhead: 25% of direct costs
    """

    def __init__(self, df: pd.DataFrame, meta: Dict[str, Any],
                 overrides: Optional[Dict[str, Any]] = None):
        """
        Args:
            df: Simulation results DataFrame.
            meta: Metadata dictionary from the CSV header.
            overrides: Optional dictionary to override EconomicsConfig values.
        """
        self.df = df
        self.meta = meta
        self.cfg = SimulationConfig()

        if overrides:
            for k, v in overrides.items():
                if hasattr(self.cfg.economics, k):
                    setattr(self.cfg.economics, k, v)

        # Extract sizing parameters from metadata
        dims = self.meta.get('dimensions', {})
        sim_args = self.meta.get('sim_args', {})
        ec = self.cfg.economics
        tc = self.cfg.tes

        self.ptc_area = dims.get('aperture_area',
                        sim_args.get('aperture_area',
                        sim_args.get('aperture', ec.ptc_cost_ref_area)))
        self.tank_diameter = dims.get('tank_diameter',
                               sim_args.get('tank_diameter', tc.tank_diameter))
        self.tank_height = dims.get('tank_height',
                             sim_args.get('tank_height', tc.tank_height))
        self.particle_diameter = dims.get('particle_diameter',
                                  sim_args.get('particle_diameter', tc.particle_diameter))
        self.void_fraction = dims.get('void_fraction',
                               sim_args.get('void_fraction', tc.void_fraction))

        # Derived sizes
        self.tank_volume = np.pi * (self.tank_diameter / 2.0)**2 * self.tank_height
        self.htf_mass = (self.tank_volume * self.void_fraction
                         * ec.htf_density_for_mass)

    # ═══════════════════════════════════════════════════════════════════
    # Component CAPEX estimates
    # ═══════════════════════════════════════════════════════════════════

    def estimate_ptc_capex(self, area: float) -> float:
        """
        PTC solar field installed cost with economy-of-scale.

        C = C_ref * A * (A / A_ref)^(n-1) * BOP_factor

        Based on: Akar & Kurup (2025), NREL DFMA bottom-up model.
        """
        ec = self.cfg.economics
        specific_cost = (ec.ptc_specific_cost_ref
                         * (area / ec.ptc_cost_ref_area)**(ec.ptc_scale_exponent - 1.0))
        solar_field_cost = specific_cost * area
        return solar_field_cost * ec.ptc_bop_factor

    def estimate_tes_capex(self, tank_volume: float, htf_mass: float,
                           tank_diameter: float, tank_height: float) -> Dict[str, float]:
        """
        Bottom-up TES tank cost estimate.

        Components:
          1. SS316 vessel (ASME VIII-1 wall thickness → mass → material cost)
          2. Multi-layer insulation (ceramic fibre + mineral wool + cladding)
          3. Fill material (crushed rock)
          4. Piping, valves, instrumentation
          5. Civil works / foundation
          6. EPC overhead

        Returns a dict with line-item breakdown + total.
        """
        ec = self.cfg.economics
        R = tank_diameter / 2.0  # inner radius

        # 1. Vessel wall thickness (ASME VIII-1, UG-27)
        P = ec.tank_design_pressure_pa
        S = ec.tank_allowable_stress_pa
        E_weld = ec.tank_weld_efficiency
        t_min = (P * R) / (S * E_weld - 0.6 * P)
        t_design = max(t_min + ec.tank_corrosion_allowance_m, 0.006)  # min 6 mm

        # Shell + heads surface areas
        A_shell = 2.0 * np.pi * R * tank_height
        A_head = 2.0 * np.pi * R**2  # approximate 2:1 ellipsoidal
        A_total_steel = A_shell + 2.0 * A_head

        # Vessel mass and material cost
        steel_volume = A_total_steel * t_design
        steel_mass = steel_volume * ec.tank_steel_density
        vessel_material_cost = steel_mass * ec.tank_ss316_price_per_kg
        vessel_installed = vessel_material_cost * ec.tank_vessel_epc_factor

        # 2. Insulation (A_shell + top head)
        A_ins = A_shell + A_head
        insulation_material = (A_ins * (ec.insulation_cost_ceramic_per_m2
                                        + ec.insulation_cost_microporous_per_m2
                                        + ec.insulation_cost_mineral_per_m2
                                        + ec.insulation_cost_cladding_per_m2))
        insulation_installed = insulation_material * ec.tank_insulation_epc_factor

        # 3. Fill material
        solid_volume = tank_volume * (1.0 - self.void_fraction)
        fill_mass_tonnes = solid_volume * self.cfg.tes.solid_density / 1000.0
        fill_material = fill_mass_tonnes * ec.fill_cost_per_tonne
        fill_installed = fill_material * ec.tank_fill_epc_factor

        # 4. Piping, valves, instrumentation (assigned to tank subsystem)
        tank_equipment_subtotal = vessel_material_cost + insulation_material + fill_material
        piping_valves = tank_equipment_subtotal * ec.piping_valves_fraction

        # 5. Civil works
        civil_works = vessel_material_cost * ec.civil_works_fraction

        # 6. HTF inventory
        htf_cost = htf_mass * ec.htf_cost_per_kg

        # Subtotal before EPC
        direct_subtotal = (vessel_installed + insulation_installed
                           + fill_installed + piping_valves + civil_works)

        # 7. EPC overhead on tank direct
        epc_overhead = direct_subtotal * ec.epc_overhead_fraction

        total_tank = direct_subtotal + epc_overhead + htf_cost

        return {
            'vessel_material': vessel_material_cost,
            'vessel_installed': vessel_installed,
            'insulation_installed': insulation_installed,
            'fill_installed': fill_installed,
            'piping_valves': piping_valves,
            'civil_works': civil_works,
            'htf_cost': htf_cost,
            'epc_overhead': epc_overhead,
            'total_tank': total_tank,
            'wall_thickness_m': t_design,
            'steel_mass_kg': steel_mass,
            'fill_mass_tonnes': fill_mass_tonnes,
        }

    def estimate_hx_capex(self, name: str, UA: float, T_op: float) -> float:
        """
        Shell-and-tube heat exchanger installed cost.

        Uses Turton et al. (2018) floating-head correlation with SS316
        material factor and CEPCI escalation.

        Args:
            name: HX identifier ('charge_hx', 'discharge_hx', 'process_hx').
            UA: Overall heat transfer coefficient × area [W/K].
            T_op: Design operating temperature [°C] (for material justification).

        Returns:
            Installed cost in 2025 USD.
        """
        ec = self.cfg.economics

        # Choose overall U based on service
        if name == 'process_hx':
            U_est = ec.hx_u_salt_zinc
        else:
            U_est = ec.hx_u_salt_salt

        # Estimate area from UA
        A_est = max(UA / U_est, 10.0)  # m², clamped to correlation min

        # Turton base purchase cost (CEPCI = 500)
        logA = np.log10(A_est)
        log10_Cp0 = ec.hx_k1 + ec.hx_k2 * logA + ec.hx_k3 * logA**2
        Cp0 = 10.0**log10_Cp0

        # Bare module (installed) cost at base CEPCI
        C_bm_base = Cp0 * (ec.hx_b1 + ec.hx_b2 * ec.hx_fm_ss316 * ec.hx_fp_default)

        # CEPCI escalation to current year
        C_installed = C_bm_base * (ec.cepci_current / ec.cepci_base) * ec.hx_cost_multiplier

        return C_installed

    def estimate_pump_capex(self, W_pump_max_kW: float) -> float:
        """
        Molten-salt centrifugal pump installed cost.

        Simplified engineering fit from Turton et al. (2018) centrifugal
        pump correlation with CSP molten salt premium and VFD.

        C = a * W^b  [USD, kW]
        """
        ec = self.cfg.economics
        if W_pump_max_kW <= 0.0:
            return 0.0

        W = max(W_pump_max_kW, 0.1)
        pump_base = ec.pump_cost_a * W**ec.pump_cost_b
        pump_with_premium = pump_base * ec.pump_molten_salt_premium
        vfd_cost = W * ec.pump_vfd_cost_per_kw

        return pump_with_premium + vfd_cost

    # ═══════════════════════════════════════════════════════════════════
    # Financial calculations
    # ═══════════════════════════════════════════════════════════════════

    def calculate_annualized_capex(self, total_capex: float) -> float:
        """Annualized capital cost via Capital Recovery Factor."""
        r = self.cfg.economics.discount_rate
        n = self.cfg.economics.lifetime
        crf = (r * (1 + r)**n) / (((1 + r)**n) - 1)
        return total_capex * crf

    # ═══════════════════════════════════════════════════════════════════
    # Main assessment
    # ═══════════════════════════════════════════════════════════════════

    def run_assessment(self) -> Dict[str, float]:
        """
        Full economic assessment: CAPEX, OPEX, LCOH.

        Returns:
            Dictionary with all economic metrics.
        """
        ec = self.cfg.economics

        # === CAPEX ===

        # 1. PTC field
        capex_ptc = self.estimate_ptc_capex(self.ptc_area)

        # 2. TES tank (full bottom-up)
        tes_detail = self.estimate_tes_capex(
            self.tank_volume, self.htf_mass,
            self.tank_diameter, self.tank_height
        )
        capex_tes = tes_detail['total_tank']

        # 3. Pumps (from post-processed 95th percentile power — not instantaneous max,
        # which reflects rare peak-DNI transients and would over-size the pump by 2-3x at high SM)
        W_pump_max = (self.df['W_pump_kW'].quantile(0.95)
                      if 'W_pump_kW' in self.df.columns else 0.0)
        capex_pumps = self.estimate_pump_capex(W_pump_max)

        # 4. Heat exchangers — use actual design-point kA from TESPy simulation metadata
        # Fall back to physically-plausible Q/dTlm estimates if metadata is missing.
        hx_kA = self.meta.get('hx_kA', {})

        def _kA_for_hx(name, fallback_Q_W, fallback_dTlm=40.0):
            val = hx_kA.get(name)
            if val is not None and val > 0:
                return float(val)
            return fallback_Q_W / fallback_dTlm

        kA_process = _kA_for_hx('process_hx', 450e3, 50.0)
        capex_hx_process = self.estimate_hx_capex('process_hx', kA_process, 480.0)

        kA_charge = _kA_for_hx('charge_hx', 250e3, 40.0)
        capex_hx_charge = self.estimate_hx_capex('charge_hx', kA_charge, 550.0)

        kA_discharge = _kA_for_hx('discharge_hx', 450e3, 40.0)
        capex_hx_discharge = self.estimate_hx_capex('discharge_hx', kA_discharge, 500.0)

        capex_hxs = capex_hx_charge + capex_hx_discharge + capex_hx_process

        # 5. Direct equipment subtotal
        direct_equipment = capex_ptc + capex_tes + capex_pumps + capex_hxs

        # 6. Piping, valves, instrumentation (on direct equipment)
        capex_piping = direct_equipment * ec.piping_valves_fraction

        # 7. EPC overhead
        direct_with_piping = direct_equipment + capex_piping
        epc_overhead = direct_with_piping * ec.epc_overhead_fraction

        # 8. Total CAPEX
        capex_total = direct_with_piping + epc_overhead

        annualized_capex = self.calculate_annualized_capex(capex_total)

        # === OPEX ===

        # Electricity (pump energy)
        total_pump_kWh = (self.df['W_pump_kW'].sum()
                          if 'W_pump_kW' in self.df.columns else 0.0)
        cost_electricity = total_pump_kWh * ec.electricity_price_per_kwh

        # Auxiliary fuel (natural gas for process + TES heater)
        # NOTE: aux_tes_energy_kJ is BLANKET HEATER consumption ONLY (active heat input).
        # Passive standby cooling heat loss is NOT included here. It is already accounted
        # for by reducing SoC — depleting the tank and forcing more Mode 3/4 use, which
        # correctly penalizes SF without double-counting. DO NOT add passive loss to OPEX.
        aux_to_proc_kWh = ((self.df['aux_to_proc_kJ'].sum() / 3600.0)
                           if 'aux_to_proc_kJ' in self.df.columns else 0.0)
        aux_tes_kWh = ((self.df['aux_tes_energy_kJ'].sum() / 3600.0)
                       if 'aux_tes_energy_kJ' in self.df.columns else 0.0)
        total_aux_kWh = aux_to_proc_kWh + aux_tes_kWh
        cost_aux_fuel = total_aux_kWh * ec.aux_fuel_price_per_kwh

        # O&M
        cost_om = capex_total * ec.om_rate_fraction

        opex_total = cost_electricity + cost_aux_fuel + cost_om

        # === Energy delivered ===
        solar_kJ = (self.df['solar_to_proc_kJ'].sum()
                    if 'solar_to_proc_kJ' in self.df.columns else 0.0)
        tes_kJ = (self.df['tes_to_proc_kJ'].sum()
                  if 'tes_to_proc_kJ' in self.df.columns else 0.0)
        aux_kJ = (self.df['aux_to_proc_kJ'].sum()
                  if 'aux_to_proc_kJ' in self.df.columns else 0.0)

        q_delivered_kWh = (solar_kJ + tes_kJ + aux_kJ) / 3600.0
        q_delivered_MWh = q_delivered_kWh / 1000.0

        # === LCOH ===
        if q_delivered_MWh > 0:
            lcoh = (annualized_capex + opex_total) / q_delivered_MWh
        else:
            lcoh = float('inf')

        results = {
            'capex_ptc': capex_ptc,
            'capex_tes': capex_tes,
            'capex_tes_breakdown': tes_detail,
            'capex_pumps': capex_pumps,
            'capex_hx_charge': capex_hx_charge,
            'capex_hx_discharge': capex_hx_discharge,
            'capex_hx_process': capex_hx_process,
            'capex_hxs': capex_hxs,
            'capex_piping': capex_piping,
            'epc_overhead': epc_overhead,
            'capex_total': capex_total,
            'annualized_capex': annualized_capex,
            'cost_electricity': cost_electricity,
            'cost_aux_fuel': cost_aux_fuel,
            'cost_om': cost_om,
            'opex_total': opex_total,
            'q_delivered_MWh': q_delivered_MWh,
            'lcoh_usd_per_MWh': lcoh
        }

        return results
