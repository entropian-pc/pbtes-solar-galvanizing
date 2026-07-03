"""
Single Simulation Entry Point
==============================
Runs a single solar thermal plant simulation with Packed Bed Thermal Energy Storage (PBTES)
and dynamic zinc pool.

Usage:
    python run_simulation.py                            # 7-day test
    python run_simulation.py --days 365                 # full year
    python run_simulation.py --days 365 --topology Series --tank_config direct
    python run_simulation.py --days 365 --tag baseline
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pbtes.config import baseline_config, zinc_pool_config
from pbtes.simulation.solver import Solver
from pbtes.reporting.plots import Reporting


def build_warmup_tmy(tmy_path='TMY.csv', days=365):
    """Prepend December (last 744 rows) before the requested days of the main year."""
    df = pd.read_csv(tmy_path)
    assert len(df) == 8760, f"TMY must have 8760 rows, got {len(df)}"
    december = df.iloc[8016:8760].copy()
    main_period = df.iloc[0:days * 24].copy()
    result = pd.concat([december, main_period], ignore_index=True)
    return result


def print_warmup_end_state(results_list):
    """Print the state at the end of warm-up (row 744, the start of the main year)."""
    if len(results_list) < 745:
        return
    last_warmup = results_list[744] if len(results_list) >= 744 else results_list[-1]
    print(f"\nWarm-up end state:")
    print(f"  TES top T:    {last_warmup.get('T_tes_top', float('nan')):.1f}°C")
    print(f"  TES bottom T: {last_warmup.get('T_tes_bottom', float('nan')):.1f}°C")
    print(f"  SoC at year start: {last_warmup.get('tes_soc_kWh', 0.0):.1f} kWh")
    print(f"  Zinc pool T:  {last_warmup.get('zinc_pool_temp', float('nan')):.1f}°C\n")


def print_monthly_breakdown(df):
    if 'time' not in df.columns:
        return
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])
    df['month'] = df['time'].dt.month
    
    print("\n" + "="*125)
    print(" MONTHLY PERFORMANCE BREAKDOWN")
    print("="*125)
    print(f"{'Month':<6} | {'SF%':<5} | {'DNI_avg':<7} | {'DNI_max':<7} | {'T_top_avg':<9} | {'T_top_max':<9} | {'T_bot_avg':<9} | {'T_bot_min':<9} | {'Q_ch_GJ':<7} | {'Q_dis_GJ':<8} | {'Q_aux_GJ':<8} | {'Mode top 3'}")
    print("-"*125)
    
    # Group by month (1 to 12)
    for m in sorted(df['month'].unique()):
        m_df = df[df['month'] == m]
        if m_df.empty:
            continue
            
        # Solar Fraction SF%
        sol_useful = m_df['solar_to_proc_kJ'].sum() + m_df['tes_to_proc_kJ'].sum()
        total_aux_tes = m_df['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in m_df.columns else 0.0
        total_demand = sol_useful + m_df['aux_to_proc_kJ'].sum() + total_aux_tes
        sf = (sol_useful / total_demand * 100) if total_demand > 0 else 0.0
        
        # DNI
        dni_avg = m_df['E'].mean()
        dni_max = m_df['E'].max()
        
        # TES temperatures
        t_top_avg = m_df['T_tes_top'].mean()
        t_top_max = m_df['T_tes_top'].max()
        t_bot_avg = m_df['T_tes_bottom'].mean()
        t_bot_min = m_df['T_tes_bottom'].min()
        
        # Energy in GJ (1 GJ = 1,000,000 kJ)
        q_ch = m_df['to_tes_kJ'].sum() / 1e6
        q_dis = m_df['tes_to_proc_kJ'].sum() / 1e6
        q_aux = (m_df['aux_to_proc_kJ'].sum() + total_aux_tes) / 1e6
        
        # Mode top 3
        mode_counts = m_df['TESmode'].astype(str).value_counts()
        total_modes = len(m_df)
        mode_pct = [f"{mode} ({count/total_modes*100:.0f}%)" for mode, count in mode_counts.head(3).items()]
        mode_str = ", ".join(mode_pct)
        
        month_name = pd.Timestamp(2022, m, 1).strftime('%B')[:3]
        
        print(f"{month_name:<6} | {sf:5.1f} | {dni_avg:7.1f} | {dni_max:7.1f} | {t_top_avg:9.1f} | {t_top_max:9.1f} | {t_bot_avg:9.1f} | {t_bot_min:9.1f} | {q_ch:7.1f} | {q_dis:8.1f} | {q_aux:8.1f} | {mode_str}")
    print("="*125 + "\n")


def run_single_simulation(
    days=7,
    topology='Parallel',
    tank_config='indirect',
    htf='INCOMP::NaK',
    tag='baseline',
    aperture=1000.0,
    tank_diameter=7.0,
    tank_height=5.0,
    particle_diameter=0.050,
    void_fraction=0.4,
    insulation_thickness=1.0,
    T_init=None,
    run_id=None,
    _progress_file=None,
    warmup=True,
    charge_margin=1.5,
    mass_steel_per_hour=None
):
    # Load baseline parameters
    tes_params, component_params, conexion_params = baseline_config()
    zinc_params = zinc_pool_config()

    # Apply overrides
    if T_init is not None:
        tes_params['Initial temperature'] = T_init

    # Apply overrides
    component_params['ptc_A'] = aperture
    tes_params['Tank diameter'] = tank_diameter
    tes_params['Tank length'] = tank_height
    tes_params['Particle diameter'] = particle_diameter
    tes_params['Void fraction'] = void_fraction
    tes_params['Insulation thickness'] = insulation_thickness
    if mass_steel_per_hour is not None:
        zinc_params['mass_steel_per_hour'] = mass_steel_per_hour

    # Build warm-up TMY if enabled
    warmup_tmy = None
    if warmup:
        # Override initial temperature to cold start
        if T_init is None:
            T_init = 300.1
        tes_params['Initial temperature'] = T_init
        warmup_tmy = build_warmup_tmy(days=days)
        print(f"\nWarm-up enabled: 31 days of December prepended ({len(warmup_tmy)} total rows)")

    # Apply HTF overrides if they differ from baseline
    if htf != 'INCOMP::NaK':
        tes_params['HTF'] = htf
        conexion_params['6_f'] = {htf: 1}
        conexion_params['13_f'] = {htf: 1}
        conexion_params['15_f'] = {htf: 1}

    # Initialize the Solver
    print(f"\nInitializing solver...")
    print(f"  Topology:    {topology}")
    print(f"  Tank Config: {tank_config}")
    print(f"  HTF:         {htf}")
    print(f"  Aperture:    {aperture} m²")
    print(f"  TES Tank:    {tank_diameter}m D x {tank_height}m H")
    
    solver = Solver(
        tes_params=tes_params,
        component_params=component_params,
        conexion_params=conexion_params,
        HTF=htf,
        system_mode='Full',
        topology=topology,
        tank_config=tank_config,
        zinc_pool_params=zinc_params,
        _run_id=run_id,
        _progress_file=_progress_file,
        charge_margin=charge_margin
    )

    # Initialize TESPy modes
    print("\nInitializing cycle design states...")
    init_temp = tes_params['Initial temperature']  # save before mutation
    solver.initialize_modes()
    solver.tes_params['Initial temperature'] = init_temp  # restore

    # Run quasi-steady simulation
    total_label = f"{31 + days}-day" if warmup else f"{days}-day"
    print(f"\nRunning {total_label} simulation (warmup={'yes' if warmup else 'no'})...")
    t_start = time.time()
    results_list = solver.run_quasi_steady_simulation(
        days_to_simulate=days,
        csv='TMY.csv',
        weather_df=warmup_tmy
    )
    elapsed = time.time() - t_start
    print(f"Simulation finished in {elapsed:.1f} seconds.")

    # Print warm-up end state before stripping
    if warmup:
        print_warmup_end_state(results_list)
        # Strip the first 744 warm-up rows (31 days of December)
        results_list = results_list[744:]
        print(f"Stripped 744 warm-up rows. Keeping {len(results_list)} main-year rows.")

    # Process and format results
    df = pd.DataFrame(results_list)
    
    # Map raw solver output fields to required CSV fields
    df['T_zinc'] = df['zinc_pool_temp']
    df['Q_zinc_hx_kW'] = df['process_hx_Q_kW']
    df['zinc_operating'] = df['time'].apply(lambda t: solver.zinc_pool.is_operating(t))

    # Reorder/select columns to comply with the results storage protocol
    # Include diagnostic columns for convergence analysis
    required_cols = [
        'time', 'E', 'Tamb', 'TESmode', 'TES_layout', 'iter_status',
        'T_ptc_out', 'T_tes_top', 'T_tes_bottom', 'T_tes_cold_top', 'T_tes_cold_bot',
        'tes_soc_kWh', 'mdot_ptc_kg_s',
        'mdot_tes_charge_kg_s', 'mdot_tes_discharge_kg_s', 'mdot_process_kg_s',
        'to_tes_kJ', 'tes_to_proc_kJ', 'solar_to_proc_kJ', 'aux_to_proc_kJ',
        'aux_tes_energy_kJ', 'ptc_total_kJ',
        'tes_heat_loss_kJ', 'ptc_heat_loss_kJ',
        'zinc_heat_loss_kJ', 'zinc_parts_kJ', 'zinc_Q_used_kW',
        'T_zinc', 'Q_zinc_hx_kW', 'zinc_operating',
        'tes_profile', 'hot_tes_profile', 'cold_tes_profile',
        'mode_initial', 'mode_final', 'attempt_count', 'attempted_modes',
        'attempts_json', 'network_converged', 'tespy_error', 'dof_report',
    ]
    
    # Ensure all required columns are present in the final DF
    for c in required_cols:
        if c not in df.columns:
            df[c] = np.nan
            
    final_df = df[required_cols].copy()

    # Serialize list/dict diagnostic columns to JSON strings for CSV compat
    def _safe_json_serialize(x):
        if x is None:
            return ''
        if isinstance(x, (list, tuple, np.ndarray)):
            result = []
            for v in x:
                if v is None:
                    result.append(None)
                    continue
                try:
                    fv = float(v)
                    result.append(fv if np.isfinite(fv) else None)
                except (TypeError, ValueError):
                    result.append(None)
            return json.dumps(result)
        if isinstance(x, dict):
            result = {}
            for k, v in x.items():
                try:
                    fv = float(v)
                    result[k] = fv if np.isfinite(fv) else None
                except (TypeError, ValueError):
                    result[k] = str(v) if v is not None else None
            return json.dumps(result)
        try:
            v = float(x)
            return json.dumps(v if np.isfinite(v) else None)
        except (TypeError, ValueError, OverflowError):
            return str(x)

    for col in ['attempted_modes', 'attempts_json', 'tes_profile', 'hot_tes_profile', 'cold_tes_profile']:
        if col in final_df.columns:
            final_df[col] = final_df[col].apply(_safe_json_serialize)

    # Construct clean file name — include dp/vf/ins/cm/msh when non-baseline to avoid collisions
    htf_clean = htf.replace('INCOMP::', '')
    dimensions = f"D{tank_diameter:.1f}_H{tank_height:.1f}_A{aperture:.0f}"
    if abs(particle_diameter - 0.050) > 0.0005:
        dimensions += f"_dp{particle_diameter:.3f}"
    if abs(void_fraction - 0.40) > 0.005:
        dimensions += f"_vf{void_fraction:.2f}"
    if abs(insulation_thickness - 1.0) > 0.01:
        dimensions += f"_ins{insulation_thickness:.2f}"
    if abs(charge_margin - 1.5) > 0.01:
        dimensions += f"_cm{charge_margin:.2f}"
    if mass_steel_per_hour is not None and abs(mass_steel_per_hour - 5000.0) > 1.0:
        dimensions += f"_msh{mass_steel_per_hour:.0f}"
    date_str = datetime.now().strftime("%Y%m%d")
    
    os.makedirs('results', exist_ok=True)
    filename = f"results/{tag}_{topology}_{tank_config}_{htf_clean}_{dimensions}_{days}d_{date_str}.csv"

    # Collect HX design-point kA values from solver (set during initialize_modes)
    hx_kA = getattr(solver, 'hx_kA', {})

    # Save CSV with the leading __meta__ line
    meta = {
        'tag': tag,
        'topology': topology,
        'tank_config': tank_config,
        'HTF': htf,
        'hx_kA': hx_kA,
        'warmup_days': 31 if warmup else 0,
        'charge_margin': charge_margin,
        'mass_steel_per_hour': mass_steel_per_hour if mass_steel_per_hour is not None else 5000.0,
        'dimensions': {
            'aperture_area': aperture,
            'tank_diameter': tank_diameter,
            'tank_height': tank_height,
            'particle_diameter': particle_diameter,
            'void_fraction': void_fraction,
            'insulation_thickness': insulation_thickness
        },
        'tes_params': tes_params,
        'component_params': component_params,
        'conexion_params': conexion_params,
        'zinc_params': zinc_params,
        'sim_args': {
            'days': days,
            'elapsed_seconds': elapsed,
            'date': date_str
        }
    }

    # Use Reporting's metadata saving logic
    rep = Reporting()
    rep.save_simulation_to_csv(
        final_df,
        filepath=filename,
        params=meta
    )
    print(f"\nResults successfully saved to: {filename}")

    # Print monthly breakdown if simulation duration is >= 30 days
    if days >= 30:
        print_monthly_breakdown(final_df)

    return final_df, filename, meta


def main():
    parser = argparse.ArgumentParser(description="Run a single quasi-steady simulation of the plant.")
    parser.add_argument('--days', type=int, default=7, help="Number of days to simulate.")
    parser.add_argument('--topology', type=str, default='Parallel', choices=['Parallel', 'Series'],
                        help="Thermodynamic cycle topology.")
    parser.add_argument('--tank_config', type=str, default='indirect', choices=['indirect', 'direct'],
                        help="Storage tank integration config.")
    parser.add_argument('--htf', type=str, default='INCOMP::NaK', help="CoolProp fluid name for the primary loops.")
    parser.add_argument('--tag', type=str, default='baseline', help="Descriptive tag for the simulation run.")
    
    # Overrides for physical dimensions
    parser.add_argument('--aperture', type=float, default=1000.0, help="PTC field aperture area in m².")
    parser.add_argument('--tank_diameter', type=float, default=7.0, help="TES internal tank diameter in m.")
    parser.add_argument('--tank_height', type=float, default=5.0, help="TES packed bed height (Tank length) in m.")
    parser.add_argument('--particle_diameter', type=float, default=0.050, help="Packed bed particle diameter in m.")
    parser.add_argument('--void_fraction', type=float, default=0.4, help="Packed bed void fraction (porosity).")
    parser.add_argument('--insulation_thickness', type=float, default=1.0, help="TES tank insulation thickness in m.")
    parser.add_argument('--T_init', type=float, default=None, help="TES uniform initial temperature override in °C.")
    parser.add_argument('--run-id', type=str, default=None, help="Isolation key for design cache (auto-generated from params if omitted).")
    parser.add_argument('--warmup', action='store_true', default=True,
                        help='Prepend December warm-up before main simulation (default: True)')
    parser.add_argument('--no-warmup', dest='warmup', action='store_false',
                        help='Skip warm-up (legacy behavior, not recommended)')
    parser.add_argument('--charge_margin', type=float, default=1.5, help="Sizing/operating margin for charge.")
    parser.add_argument('--mass_steel_per_hour', type=float, default=None, help="Zinc pool steel throughput rate override in kg/h.")
    
    args = parser.parse_args()

    run_single_simulation(
        days=args.days,
        topology=args.topology,
        tank_config=args.tank_config,
        htf=args.htf,
        tag=args.tag,
        aperture=args.aperture,
        tank_diameter=args.tank_diameter,
        tank_height=args.tank_height,
        particle_diameter=args.particle_diameter,
        void_fraction=args.void_fraction,
        insulation_thickness=args.insulation_thickness,
        T_init=args.T_init,
        run_id=args.run_id,
        warmup=args.warmup,
        charge_margin=args.charge_margin,
        mass_steel_per_hour=args.mass_steel_per_hour
    )


if __name__ == '__main__':
    main()
