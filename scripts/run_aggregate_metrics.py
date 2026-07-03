"""
run_aggregate_metrics.py

Post-processing pipeline: aggregates all simulation result CSVs into a single
metrics table (parametric_metrics.csv) suitable for figure generation.

For each CSV in results/:
  1. Load data + metadata
  2. Compute pump power (if not present)
  3. Run economic assessment (LCOH)
  4. Run exergoeconomic assessment (optional)
  5. Extract all aggregate metrics per sweep plan 7.2

Output: results/parametric_metrics.csv

Usage:
    python scripts/run_aggregate_metrics.py
    python scripts/run_aggregate_metrics.py --files "results/sweep_*.csv"
    python scripts/run_aggregate_metrics.py --manifest results/parametric_manifest.csv
    python scripts/run_aggregate_metrics.py --skip-economics --skip-exergo
"""

import sys
import os
import glob
import argparse
import json
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pbtes.analysis.results_reader import load_results
from pbtes.analysis.postprocess import calculate_system_pump_power
from pbtes.analysis.economics import EconomicAssessment

OUTPUT_PATH = os.path.join('results', 'parametric_metrics.csv')


def _safe_sum(col_series):
    return col_series.sum() if not col_series.isna().all() else 0.0


def extract_metrics(df: pd.DataFrame, meta: dict, skip_economics: bool = False,
                    skip_exergo: bool = False) -> dict:
    """
    Extract all aggregate metrics from a single simulation result.

    Parameters
    ----------
    df : pd.DataFrame
        Simulation timeseries data.
    meta : dict
        Metadata dictionary from the CSV header.
    skip_economics : bool
        Skip LCOH computation.
    skip_exergo : bool
        Skip exergoeconomic computation.

    Returns
    -------
    metrics : dict
        Flat dictionary of aggregate metrics.
    """
    sim_args = meta.get('sim_args', {})
    dims = meta.get('dimensions', {})

    topology = meta.get('topology', sim_args.get('topology', 'Parallel'))
    tank_config = meta.get('tank_config', sim_args.get('tank_config', 'indirect'))
    htf = meta.get('HTF', meta.get('htf', sim_args.get('htf', 'INCOMP::NaK')))
    tag = meta.get('tag', '')
    days = sim_args.get('days', 7)

    aperture = dims.get('aperture_area', sim_args.get('aperture_area', sim_args.get('aperture', 1000.0)))
    tank_diameter = dims.get('tank_diameter', sim_args.get('tank_diameter', 7.0))
    tank_height = dims.get('tank_height', sim_args.get('tank_height', 5.0))
    particle_diameter = dims.get('particle_diameter', sim_args.get('particle_diameter', 0.050))
    void_fraction = dims.get('void_fraction', sim_args.get('void_fraction', 0.40))
    insulation_thickness = dims.get('insulation_thickness', sim_args.get('insulation_thickness', 1.0))

    tes_volume = np.pi * (tank_diameter / 2.0)**2 * tank_height
    solar_multiple = aperture / 1000.0

    # Energy totals (kJ)
    solar_to_proc = _safe_sum(df.get('solar_to_proc_kJ', pd.Series([0])))
    tes_to_proc = _safe_sum(df.get('tes_to_proc_kJ', pd.Series([0])))
    aux_to_proc = _safe_sum(df.get('aux_to_proc_kJ', pd.Series([0])))
    aux_tes = _safe_sum(df.get('aux_tes_energy_kJ', pd.Series([0])))
    to_tes = _safe_sum(df.get('to_tes_kJ', pd.Series([0])))
    ptc_total = _safe_sum(df.get('ptc_total_kJ', pd.Series([0])))

    q_solar_useful = solar_to_proc + tes_to_proc
    q_aux_total = aux_to_proc + aux_tes
    q_total_demand = q_solar_useful + q_aux_total

    sf_thermal = (q_solar_useful / q_total_demand * 100.0) if q_total_demand > 0 else 0.0
    # RTE can exceed 100% when initial thermal inventory is depleted (discharge > charge).
    # Correct by subtracting the initial→final SoC drop from the discharge side.
    round_trip_eff_raw = (tes_to_proc / to_tes * 100.0) if to_tes > 0 else 0.0
    soc_initial = df['tes_soc_kWh'].iloc[0] if 'tes_soc_kWh' in df.columns else 0.0
    soc_final   = df['tes_soc_kWh'].iloc[-1] if 'tes_soc_kWh' in df.columns else 0.0
    inventory_delta_kWh = max(0.0, soc_initial - soc_final)
    inventory_delta_kJ = inventory_delta_kWh * 3600.0
    tes_from_charge = max(0.0, tes_to_proc - inventory_delta_kJ)
    round_trip_eff = (tes_from_charge / to_tes * 100.0) if to_tes > 0 else 0.0
    rte_corrected = min(100.0, round_trip_eff_raw)

    # Convergence
    n_total = len(df)
    n_converged = int((df['iter_status'] == 'converged').sum()) if 'iter_status' in df.columns else n_total
    n_failed = int((df['iter_status'] == 'failed').sum()) if 'iter_status' in df.columns else 0
    convergence_rate = (n_converged / n_total * 100.0) if n_total > 0 else 100.0

    # Temperature means (operational: DNI > 10 W/m2 or mdot > 0)
    operational = pd.Series(True, index=df.index)
    if 'E' in df.columns:
        operational = operational & (df['E'] > 10)
    if 'mdot_ptc_kg_s' in df.columns:
        has_flow = (df['mdot_ptc_kg_s'].fillna(0) > 0) | \
                   (df.get('mdot_tes_charge_kg_s', pd.Series(0)).fillna(0) > 0) | \
                   (df.get('mdot_tes_discharge_kg_s', pd.Series(0)).fillna(0) > 0)
        operational = operational | has_flow

    t_tes_top_mean = df.loc[operational, 'T_tes_top'].mean() if 'T_tes_top' in df.columns else np.nan
    t_tes_bottom_mean = df.loc[operational, 'T_tes_bottom'].mean() if 'T_tes_bottom' in df.columns else np.nan
    t_tes_top_max = df['T_tes_top'].max() if 'T_tes_top' in df.columns else np.nan
    t_tes_bottom_min = df['T_tes_bottom'].min() if 'T_tes_bottom' in df.columns else np.nan
    t_zinc_mean = df['T_zinc'].mean() if 'T_zinc' in df.columns else np.nan

    # Mode hours
    mode_hours = {}
    if 'TESmode' in df.columns:
        mode_counts = df['TESmode'].astype(str).value_counts()
        for mode, count in mode_counts.items():
            mode_hours[f'mode_{mode}_hours'] = int(count)
    total_mode_hours = sum(mode_hours.values()) if mode_hours else n_total

    # SoC
    soc_mean = df['tes_soc_kWh'].mean() if 'tes_soc_kWh' in df.columns else np.nan
    soc_max = df['tes_soc_kWh'].max() if 'tes_soc_kWh' in df.columns else np.nan

    # Zinc pool metrics
    zinc_operating_hours = int(df['zinc_operating'].sum()) if 'zinc_operating' in df.columns else 0
    q_zinc_hx_mean = df['Q_zinc_hx_kW'].mean() if 'Q_zinc_hx_kW' in df.columns else np.nan

    # DNI stats
    dni_mean = df['E'].mean() if 'E' in df.columns else np.nan
    dni_total = _safe_sum(df.get('E', pd.Series([0])))  # W/m2 * hours -> Wh/m2

    metrics = {
        'source_file': '',
        'topology': topology,
        'tank_config': tank_config,
        'htf': htf,
        'tag': tag,
        'days': days,
        'aperture_m2': aperture,
        'tank_diameter_m': tank_diameter,
        'tank_height_m': tank_height,
        'particle_diameter_m': particle_diameter,
        'void_fraction': void_fraction,
        'insulation_thickness_m': insulation_thickness,
        'tes_volume_m3': tes_volume,
        'solar_multiple': solar_multiple,
        'sf_thermal_pct': sf_thermal,
        'q_solar_GJ': q_solar_useful / 1e6,
        'q_charge_GJ': to_tes / 1e6,
        'q_discharge_GJ': tes_to_proc / 1e6,
        'q_aux_proc_GJ': aux_to_proc / 1e6,
        'q_aux_tes_GJ': aux_tes / 1e6,
        'q_ptc_GJ': ptc_total / 1e6,
        'round_trip_eff_pct': round_trip_eff,
        'rte_corrected_pct': rte_corrected,
        'n_timesteps': n_total,
        'n_converged': n_converged,
        'n_failed': n_failed,
        'convergence_rate_pct': convergence_rate,
        't_tes_top_mean_C': t_tes_top_mean,
        't_tes_bottom_mean_C': t_tes_bottom_mean,
        't_tes_top_max_C': t_tes_top_max,
        't_tes_bottom_min_C': t_tes_bottom_min,
        't_zinc_mean_C': t_zinc_mean,
        'soc_mean_kWh': soc_mean,
        'soc_max_kWh': soc_max,
        'zinc_operating_hours': zinc_operating_hours,
        'q_zinc_hx_mean_kW': q_zinc_hx_mean,
        'dni_mean_Wm2': dni_mean,
        'dni_total_Whm2': dni_total,
        'lcoh_usd_per_MWh': np.nan,
        'capex_total': np.nan,
        'opex_total': np.nan,
        'annualized_capex': np.nan,
        'q_delivered_MWh': np.nan,
        'sf_net_pct': np.nan,
        'eta_exergy_pct': np.nan,
        'Ex_destruction_MWh': np.nan,
    }
    metrics.update(mode_hours)

    # Pump power (post-process)
    if 'W_pump_kW' not in df.columns:
        try:
            df = calculate_system_pump_power(df, meta)
        except Exception:
            pass

    pump_total_kWh = _safe_sum(df.get('W_pump_kW', pd.Series([0])))  # kW * hours

    # Net solar fraction (pump parasitics as electrical import)
    pump_equiv_kJ = pump_total_kWh * 3600.0  # kWh -> kJ (electrical equivalent)
    sf_net = (q_solar_useful / (q_solar_useful + q_aux_total + pump_equiv_kJ * 0.3) * 100.0) \
        if (q_solar_useful + q_aux_total) > 0 else sf_thermal
    metrics['sf_net_pct'] = sf_net
    metrics['pump_total_kWh'] = pump_total_kWh
    metrics['W_pump_max_kW'] = float(df['W_pump_kW'].max()) if 'W_pump_kW' in df.columns else 0.0

    # Economics
    if not skip_economics:
        try:
            econ = EconomicAssessment(df, meta)
            econ_res = econ.run_assessment()
            metrics['lcoh_usd_per_MWh'] = econ_res.get('lcoh_usd_per_MWh', np.nan)
            metrics['capex_total'] = econ_res.get('capex_total', np.nan)
            metrics['opex_total'] = econ_res.get('opex_total', np.nan)
            metrics['annualized_capex'] = econ_res.get('annualized_capex', np.nan)
            metrics['q_delivered_MWh'] = econ_res.get('q_delivered_MWh', np.nan)
        except Exception as e:
            print(f"    [WARN] Economics failed: {e}")

    # Exergoeconomics
    if not skip_exergo:
        try:
            from pbtes.analysis.exergoeconomics import ExergoeconomicAssessment
            exergo = ExergoeconomicAssessment(df, meta)
            ex_res = exergo.run_exergoeconomic_assessment()
            metrics['eta_exergy_pct'] = ex_res.get('eta_exergy', np.nan)
            metrics['Ex_destruction_MWh'] = ex_res.get('Ex_destruction_MWh', np.nan)
        except Exception as e:
            print(f"    [WARN] Exergoeconomics failed: {e}")

    return metrics


def gather_csv_files(files_glob: str = None, manifest_path: str = None) -> list:
    """Gather list of CSV file paths to process."""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    files = []

    if files_glob:
        matches = glob.glob(files_glob)
        files.extend([f for f in matches if os.path.isfile(f)])
    elif manifest_path and os.path.exists(manifest_path):
        df_manifest = pd.read_csv(manifest_path)
        if 'output_file' in df_manifest.columns:
            ok_files = df_manifest.loc[
                df_manifest['status'].isin(['ok', 'failed']),
                'output_file'
            ].dropna().tolist()
            files.extend([f for f in ok_files if os.path.exists(f)])
    else:
        # Auto-discover all CSVs in results/
        if os.path.isdir(results_dir):
            for f in sorted(os.listdir(results_dir)):
                if f.endswith('.csv') and not f.startswith('_'):
                    if ('_processed' not in f and '_exergo' not in f
                            and 'parametric_manifest' not in f
                            and 'parametric_metrics' not in f
                            and 'parametric_economic_sensitivities' not in f):
                        fp = os.path.join(results_dir, f)
                        files.append(fp)

    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate simulation result CSVs into parametric_metrics.csv')
    parser.add_argument('--files', type=str, default=None,
                        help='Glob pattern for CSV files to process.')
    parser.add_argument('--manifest', type=str, default=None,
                        help='Path to parametric_manifest.csv (reads output_file column).')
    parser.add_argument('--out', type=str, default=OUTPUT_PATH,
                        help='Output CSV path (default: results/parametric_metrics.csv).')
    parser.add_argument('--skip-economics', action='store_true',
                        help='Skip LCOH computation (faster).')
    parser.add_argument('--skip-exergo', action='store_true',
                        help='Skip exergoeconomic computation (faster).')
    args = parser.parse_args()

    files = gather_csv_files(args.files, args.manifest)

    if not files:
        print("No result CSV files found. Run simulations first or specify --files/--manifest.")
        return

    print(f"Processing {len(files)} result files...")
    records = []
    errors = []

    for fp in files:
        fname = os.path.basename(fp)
        print(f"  {fname} ...", end=' ', flush=True)
        try:
            df, meta = load_results(fp)
            m = extract_metrics(df, meta,
                                skip_economics=args.skip_economics,
                                skip_exergo=args.skip_exergo)
            m['source_file'] = fp
            records.append(m)

            sf_str = f"{m['sf_thermal_pct']:.1f}%" if not np.isnan(m['sf_thermal_pct']) else 'N/A'
            conv_str = f"{m['convergence_rate_pct']:.1f}%"
            lcoh_str = f"${m['lcoh_usd_per_MWh']:.1f}/MWh" if not np.isnan(m['lcoh_usd_per_MWh']) else ''
            print(f"SF={sf_str}  Conv={conv_str}  {lcoh_str}")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append((fp, str(e)))

    if not records:
        print("No metrics extracted.")
        return

    df_metrics = pd.DataFrame(records)
    df_metrics.sort_values(['topology', 'aperture_m2', 'tank_diameter_m', 'tank_height_m'], inplace=True)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df_metrics.to_csv(args.out, index=False)

    print(f"\n{'='*60}")
    print(f" Saved {len(df_metrics)} rows to {args.out}")
    if errors:
        print(f" {len(errors)} files failed:")
        for fp, err in errors:
            print(f"   - {os.path.basename(fp)}: {err}")
    print(f"{'='*60}")

    # Quick summary
    print(f"\n{'='*60}")
    print(" SUMMARY")
    print(f"{'='*60}")
    ok = df_metrics.dropna(subset=['sf_thermal_pct'])
    if not ok.empty:
        best_sf = ok.loc[ok['sf_thermal_pct'].idxmax()]
        print(f" Best SF:  {best_sf['sf_thermal_pct']:.1f}%  "
              f"(D={best_sf['tank_diameter_m']:.1f}m, H={best_sf['tank_height_m']:.1f}m, "
              f"A={best_sf['aperture_m2']:.0f}m2, {best_sf['topology']})")

    lcoh_ok = df_metrics.dropna(subset=['lcoh_usd_per_MWh'])
    if not lcoh_ok.empty:
        best_lcoh = lcoh_ok.loc[lcoh_ok['lcoh_usd_per_MWh'].idxmin()]
        print(f" Best LCOH: ${best_lcoh['lcoh_usd_per_MWh']:.1f}/MWh  "
              f"(D={best_lcoh['tank_diameter_m']:.1f}m, H={best_lcoh['tank_height_m']:.1f}m, "
              f"A={best_lcoh['aperture_m2']:.0f}m2)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
