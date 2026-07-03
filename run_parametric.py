"""
Parametric Sweep Entry Point (Robust & Resumable)
===================================================
Runs parametric sweeps over design and physical variables by calling the single-simulation
logic from run_simulation.py in a loop.

Features:
  - Manifest Checkpointing: Keeps state in results/parametric_manifest.csv. If stopped,
    re-running will automatically resume from the last pending simulation.
  - Fault Tolerance: If a simulation fails due to a solver convergence error or physics singularity,
    it logs the failure and traceback, saves state, and continues to the next run.
  - Automatically resets interrupted runs (left in state 'running' from a crash/kill).

Usage:
    python run_parametric.py --sweep topology       # Parallel vs Series, direct vs indirect
    python run_parametric.py --sweep aperture       # aperture area sweep
    python run_parametric.py --sweep tes_volume     # tank D x H grid (30 points)
    python run_parametric.py --sweep physical_sens  # particle diameter, void fraction, insulation
    python run_parametric.py --sweep htf            # primary NaK vs Air baseline
    python run_parametric.py --sweep full           # all of the sweeps combined

Optional overrides and controls:
    --days          Number of simulation days per sweep point (default: 365)
    --tag           Result file tag prefix (default: 'sweep')
    --retry-failed  Force-retry failed simulations instead of skipping them
    --reset-manifest Archive the existing manifest and start a fresh sweep grid
    --parallel N    Run N simulations concurrently using multiprocessing (default: 1, sequential)
    --job-range     Process only a slice of pending jobs (format: 'start:end')
    --no-progress   Disable live dashboard (plain text output)
"""

import os
import sys
import argparse
import json
import traceback
import time
from datetime import datetime
import pandas as pd
import numpy as np

# Add root directory to sys.path so we can import run_simulation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_simulation import run_single_simulation

# ── Worker Function (module-level, required for multiprocessing 'spawn') ───────

def _worker_run_job(job: dict) -> dict:
    """Execute a single simulation job in a worker process. Returns structured result."""
    t0 = time.time()
    try:
        run_id = generate_run_id(job)
        df_res, filename, meta = run_single_simulation(
            days=int(job['days']),
            topology=job['topology'],
            tank_config=job['tank_config'],
            htf=job['htf'],
            tag=job['tag'],
            aperture=float(job['aperture']),
            tank_diameter=float(job['tank_diameter']),
            tank_height=float(job['tank_height']),
            particle_diameter=float(job['particle_diameter']),
            void_fraction=float(job['void_fraction']),
            insulation_thickness=float(job['insulation_thickness']),
            run_id=run_id,
            charge_margin=float(job.get('charge_margin', 1.5)),
            mass_steel_per_hour=float(job['mass_steel_per_hour']) if 'mass_steel_per_hour' in job and job['mass_steel_per_hour'] is not None and not pd.isna(job['mass_steel_per_hour']) else None
        )
        elapsed = time.time() - t0

        sol_useful = df_res['solar_to_proc_kJ'].sum() + df_res['tes_to_proc_kJ'].sum()
        aux_proc = df_res['aux_to_proc_kJ'].sum()
        aux_tes = df_res['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in df_res.columns else 0.0
        total_aux = aux_proc + aux_tes
        total_demand = sol_useful + total_aux
        sf = (sol_useful / total_demand * 100.0) if total_demand > 0 else 0.0
        n_failed = int((df_res['iter_status'] == 'failed').sum()) if 'iter_status' in df_res.columns else 0

        return {
            'status': 'ok',
            'job_id': job['job_id'],
            'output_file': filename,
            'solar_fraction_pct': round(sf, 2),
            'total_solar_kJ': round(sol_useful, 1),
            'total_aux_kJ': round(total_aux, 1),
            'total_tes_discharge_kJ': round(df_res['tes_to_proc_kJ'].sum(), 1),
            'convergence_errors': n_failed,
            'elapsed_seconds': round(elapsed, 1),
            'error_message': '',
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            'status': 'failed',
            'job_id': job.get('job_id', 'unknown'),
            'output_file': '',
            'solar_fraction_pct': np.nan,
            'total_solar_kJ': np.nan,
            'total_aux_kJ': np.nan,
            'total_tes_discharge_kJ': np.nan,
            'convergence_errors': np.nan,
            'elapsed_seconds': round(elapsed, 1),
            'error_message': str(e).replace('\n', ' '),
        }

# ── Baseline Parameter Definition ─────────────────────────────────────────────
BASELINE_PARAMS = {
    'topology': 'Parallel',
    'tank_config': 'indirect',
    'htf': 'INCOMP::NaK',
    'aperture': 1000.0,
    'tank_diameter': 7.0,
    'tank_height': 5.0,
    'particle_diameter': 0.050,
    'void_fraction': 0.40,
    'insulation_thickness': 1.0,
}

# ── Sweep parameter grids ─────────────────────────────────────────────────────
APERTURE_SWEEP = [500.0, 750.0, 1000.0, 1500.0, 2000.0, 3000.0]

TES_DIAMETER_SWEEP = [4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
TES_HEIGHT_SWEEP   = [3.0, 4.0, 5.0, 6.0, 8.0]

TOPOLOGY_COMBOS = [
    ('Parallel', 'indirect'),
    ('Series',   'direct'),
]

PARTICLE_SWEEP = [0.03, 0.05, 0.07, 0.10]
VOID_SWEEP = [0.35, 0.40, 0.45]
INSULATION_SWEEP = [0.5, 0.75, 1.0, 1.25]

HTF_SWEEP = ['INCOMP::NaK', 'Air']

# ── Manifest & State Management ───────────────────────────────────────────────

MANIFEST_PATH = os.path.join('results', 'parametric_manifest.csv')

# Detect if running inside Spyder/IPython for dashboard output
def _is_spyder() -> bool:
    try:
        __IPYTHON__
        import spyder
        return True
    except (NameError, ImportError):
        return False
    except Exception:
        return False

_IN_SPYDER = _is_spyder()

def _dashboard_clear():
    """Clear the dashboard region. Uses IPython.clear_output in Spyder, ANSI in terminal."""
    if _IN_SPYDER:
        try:
            from IPython.display import clear_output
            clear_output(wait=True)
        except Exception:
            pass
    else:
        try:
            print('\033[2J\033[H', end='')
        except Exception:
            print('\n' + '-' * 40)

def _print_dashboard(df_manifest, batch_start, jobs_to_run, current_idx, current_job_id, job_status, sf_pct, elapsed_job, n_errors, total_error):
    """Print a compact live-status dashboard. Called after each job completion."""
    total_jobs = len(df_manifest)
    n_ok = int((df_manifest['status'] == 'ok').sum())
    n_failed = int((df_manifest['status'] == 'failed').sum())
    n_running = int((df_manifest['status'] == 'running').sum())
    n_pending = int((df_manifest['status'] == 'pending').sum())
    
    batch_elapsed = time.time() - batch_start
    if current_idx > 0 and current_idx <= len(jobs_to_run):
        eta_remaining = (batch_elapsed / current_idx) * (len(jobs_to_run) - current_idx)
    else:
        eta_remaining = 0.0
    
    elapsed_str = f"{int(batch_elapsed // 3600)}h {int((batch_elapsed % 3600) // 60)}m"
    eta_str = f"{int(eta_remaining // 3600)}h {int((eta_remaining % 3600) // 60)}m"
    
    _dashboard_clear()
    
    lines = []
    lines.append("=" * 78)
    lines.append(f"  PBTES PARAMETRIC SWEEP -- Live Status")
    lines.append("=" * 78)
    lines.append(f"  Elapsed: {elapsed_str:<10}  ETA remaining: {eta_str:<10}  Progress: {current_idx}/{len(jobs_to_run)} jobs")
    lines.append("=" * 78)
    lines.append(f"  Completed: {n_ok:<4}  Failed: {n_failed:<4}  Running: {n_running:<4}  Pending: {n_pending:<4}")
    lines.append("=" * 78)
    lines.append(f"  {'Last job':<30} {'SF%':>8}  {'Status':<10}  {'Time':<10}  {'Errors':>6}")
    lines.append(f"  {'-'*30}  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*6}")
    
    # Show last completed job
    jid_short = current_job_id if len(current_job_id) <= 30 else current_job_id[:27] + "..."
    sf_str = f"{sf_pct:.1f}" if sf_pct is not None else "   N/A"
    job_time_str = f"{elapsed_job:.0f}s" if elapsed_job is not None else "   --"
    err_str = f"{n_errors}" if n_errors is not None else "--"
    lines.append(f"  {jid_short:<30} {sf_str:>8}  {job_status:<10}  {job_time_str:<10}  {err_str:>6}")
    
    # Show last 3 completed jobs from manifest
    df_ok = df_manifest[df_manifest['status'] == 'ok']
    recent = df_ok.tail(3)
    if len(recent) > 0:
        lines.append(f"  {'-'*30}  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*6}")
        lines.append(f"  Recent completions:")
        for _, rrow in recent.iterrows():
            rjid = rrow.get('job_id', '')
            rjid_short = rjid if len(rjid) <= 30 else rjid[:27] + "..."
            sf = rrow.get('solar_fraction_pct', np.nan)
            rf_str = f"{sf:.1f}" if not pd.isna(sf) else "   N/A"
            rtime = rrow.get('elapsed_seconds', np.nan)
            rt_str = f"{rtime:.0f}s" if not pd.isna(rtime) else "   --"
            rerr = rrow.get('convergence_errors', np.nan)
            re_str = f"{int(rerr)}" if not pd.isna(rerr) else "--"
            lines.append(f"    {rjid_short:<28} {rf_str:>8}  {'ok':<10}  {rt_str:<10}  {re_str:>6}")
    
    lines.append("=" * 78)
    
    if total_error:
        lines.append(f"  [!] Error: {total_error}")
    
    print('\n'.join(lines))


def get_job_id(job: dict) -> str:
    """Generate a unique job ID string based on all configuration parameters."""
    htf_clean = job['htf'].replace('INCOMP::', '')
    cm = job.get('charge_margin', 1.5)
    cm_str = f"_cm{cm:.2f}" if abs(cm - 1.5) > 0.01 else ""
    msh = job.get('mass_steel_per_hour')
    msh_str = f"_msh{msh:.0f}" if msh is not None and not pd.isna(msh) and abs(msh - 5000.0) > 1.0 else ""
    return (
        f"{job['tag']}_{job['topology']}_{job['tank_config']}_{htf_clean}_"
        f"D{job['tank_diameter']:.1f}_H{job['tank_height']:.1f}_A{job['aperture']:.0f}_"
        f"dp{job['particle_diameter']:.3f}_vf{job['void_fraction']:.2f}_ins{job['insulation_thickness']:.2f}"
        f"{cm_str}{msh_str}_{job['days']}d"
    )

def generate_run_id(job: dict) -> str:
    """Generate a deterministic, filesystem-safe cache isolation key for a job."""
    htf_clean = job['htf'].replace('INCOMP::', '').replace('::', '_')
    cm = job.get('charge_margin', 1.5)
    cm_suffix = f"_cm{cm:.2f}" if abs(cm - 1.5) > 0.01 else ""
    msh = job.get('mass_steel_per_hour')
    msh_suffix = f"_msh{msh:.0f}" if msh is not None and not pd.isna(msh) and abs(msh - 5000.0) > 1.0 else ""
    return (
        f"{job['topology']}_{job['tank_config']}_{htf_clean}_"
        f"D{float(job['tank_diameter']):.1f}_H{float(job['tank_height']):.1f}_"
        f"A{float(job['aperture']):.0f}_"
        f"dp{float(job['particle_diameter']):.3f}_vf{float(job['void_fraction']):.2f}_ins{float(job['insulation_thickness']):.2f}"
        f"{cm_suffix}{msh_suffix}"
    )

def generate_sweep_grid(sweep_type: str, days: int, tag: str) -> list:
    """Generate a list of unique job dictionaries for the requested sweep type."""
    jobs = []

    def create_job(**overrides):
        job = BASELINE_PARAMS.copy()
        job.update(overrides)
        job['days'] = days
        job['tag'] = tag
        job['job_id'] = get_job_id(job)
        return job

    # 1. Aperture Area Sweep
    if sweep_type in ['aperture', 'full']:
        for ap in APERTURE_SWEEP:
            jobs.append(create_job(aperture=ap))

    # 2. TES Tank Diameter & Height Grid (30 points)
    if sweep_type in ['tes_volume', 'full']:
        for D in TES_DIAMETER_SWEEP:
            for H in TES_HEIGHT_SWEEP:
                jobs.append(create_job(tank_diameter=D, tank_height=H))

    # 3. Topologies Comparison (PI vs SD)
    if sweep_type in ['topology', 'full']:
        for top, tc in TOPOLOGY_COMBOS:
            jobs.append(create_job(topology=top, tank_config=tc))

    # 4. Packed Bed Physical Sensitivities (Sequential variations from baseline)
    if sweep_type in ['physical_sens', 'full']:
        for dp in PARTICLE_SWEEP:
            jobs.append(create_job(particle_diameter=dp))
        for vf in VOID_SWEEP:
            jobs.append(create_job(void_fraction=vf))
        for ins in INSULATION_SWEEP:
            jobs.append(create_job(insulation_thickness=ins))

    # 5. HTF comparison baseline
    if sweep_type in ['htf', 'full']:
        for h in HTF_SWEEP:
            jobs.append(create_job(htf=h))

    # Remove duplicate combinations while maintaining sequence order
    seen = set()
    unique_jobs = []
    for j in jobs:
        # Create a unique parameter signature key
        key = (
            j['topology'], j['tank_config'], j['htf'], j['aperture'],
            j['tank_diameter'], j['tank_height'], j['particle_diameter'],
            j['void_fraction'], j['insulation_thickness'], j['days'], j['tag']
        )
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    return unique_jobs

def load_or_create_manifest(sweep_type: str, days: int, tag: str, reset: bool = False) -> pd.DataFrame:
    """Load existing manifest, reset interrupted jobs, append new grid combinations, or create a fresh one."""
    os.makedirs('results', exist_ok=True)
    grid_jobs = generate_sweep_grid(sweep_type, days, tag)
    df_grid = pd.DataFrame(grid_jobs)

    # Initialize metadata and tracking columns
    tracking_cols = {
        'status': 'pending',
        'elapsed_seconds': np.nan,
        'output_file': '',
        'error_message': '',
        'solar_fraction_pct': np.nan,
        'total_solar_kJ': np.nan,
        'total_aux_kJ': np.nan,
        'total_tes_discharge_kJ': np.nan,
        'convergence_errors': np.nan,
        'timestamp': ''
    }
    for col, default in tracking_cols.items():
        df_grid[col] = default

    if os.path.exists(MANIFEST_PATH) and not reset:
        print(f"Loading existing manifest from: {MANIFEST_PATH}")
        try:
            # Recover from orphaned .tmp manifest if it exists (interrupted write)
            tmp_path = MANIFEST_PATH + ".tmp"
            if os.path.exists(tmp_path):
                import stat
                main_mtime = os.path.getmtime(MANIFEST_PATH) if os.path.exists(MANIFEST_PATH) else 0
                tmp_mtime = os.path.getmtime(tmp_path)
                if tmp_mtime > main_mtime:
                    print(f"  -> Recovering from orphaned .tmp manifest (newer than main).")
                    try:
                        os.remove(MANIFEST_PATH)
                    except Exception:
                        pass
                    os.rename(tmp_path, MANIFEST_PATH)
                else:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            df_existing = pd.read_csv(MANIFEST_PATH)
            
            # Reset any job that was left as 'running' (interrupted run)
            running_mask = df_existing['status'] == 'running'
            if running_mask.any():
                print(f"  -> Resetting {running_mask.sum()} interrupted 'running' job(s) back to 'pending'.")
                for ridx in df_existing[running_mask].index:
                    row = df_existing.loc[ridx]
                    # Delete partial output CSV if it exists
                    out_file = row.get('output_file', '')
                    if isinstance(out_file, str) and out_file and os.path.exists(out_file):
                        try:
                            os.remove(out_file)
                            print(f"     Deleted partial output: {out_file}")
                        except Exception:
                            pass
                    # Delete orphaned design cache directory
                    if 'job_id' in row and isinstance(row['job_id'], str):
                        run_id = generate_run_id(row.to_dict())
                        cache_dir = os.path.join('.tespy_cache', run_id)
                        if os.path.isdir(cache_dir):
                            try:
                                import shutil
                                shutil.rmtree(cache_dir, ignore_errors=True)
                                print(f"     Deleted orphaned cache: {cache_dir}")
                            except Exception:
                                pass
                df_existing.loc[running_mask, 'status'] = 'pending'
                df_existing.loc[running_mask, 'error_message'] = 'Interrupted execution — restarting'
                df_existing.loc[running_mask, 'output_file'] = ''
                df_existing.loc[running_mask, 'elapsed_seconds'] = np.nan

            # Ensure all grid jobs are present in the manifest
            # Use job_id as the primary key
            merged_list = []
            existing_jobs = {row['job_id']: row.to_dict() for _, row in df_existing.iterrows()}
            
            for _, grid_row in df_grid.iterrows():
                jid = grid_row['job_id']
                if jid in existing_jobs:
                    merged_list.append(existing_jobs[jid])
                else:
                    merged_list.append(grid_row.to_dict())
            
            df_manifest = pd.DataFrame(merged_list)
            # Save right away to persist any resets
            df_manifest.to_csv(MANIFEST_PATH, index=False)
            return df_manifest
        except Exception as e:
            print(f"[Warning] Failed to parse existing manifest: {e}. Recreating...")
            
    if reset and os.path.exists(MANIFEST_PATH):
        archive_path = f"{os.path.splitext(MANIFEST_PATH)[0]}_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        os.rename(MANIFEST_PATH, archive_path)
        print(f"Archived existing manifest to: {archive_path}")

    # Create new manifest file
    print(f"Creating a new manifest with {len(df_grid)} jobs.")
    df_grid.to_csv(MANIFEST_PATH, index=False)
    return df_grid

def save_manifest_state(df_manifest: pd.DataFrame):
    """Write the manifest dataframe atomically to disk to prevent loss of state."""
    # Write to a temp file first, then replace (prevents file corruption on sudden stops)
    temp_path = MANIFEST_PATH + ".tmp"
    df_manifest.to_csv(temp_path, index=False)
    if os.path.exists(temp_path):
        if os.path.exists(MANIFEST_PATH):
            os.remove(MANIFEST_PATH)
        os.rename(temp_path, MANIFEST_PATH)

# ── Core Sweep Execution Loop ─────────────────────────────────────────────────

def execute_sweeps(sweep_type: str, days: int, tag: str, retry_failed: bool = False,
                   reset_manifest: bool = False, job_range: str = None,
                   no_progress: bool = False, parallel_workers: int = 1):
    """Iterates through jobs in the manifest, executes them safely, and captures results."""
    df_manifest = load_or_create_manifest(sweep_type, days, tag, reset=reset_manifest)

    # Filter pending jobs (and failed if retry_failed is specified)
    jobs_to_run = []
    for idx, row in df_manifest.iterrows():
        status = row['status']
        if status == 'pending':
            jobs_to_run.append(idx)
        elif status == 'failed' and retry_failed:
            print(f"Queueing failed job for retry: {row['job_id']}")
            df_manifest.at[idx, 'status'] = 'pending'
            df_manifest.at[idx, 'error_message'] = ''
            jobs_to_run.append(idx)

    # Apply job range slicing if specified (format: "start:end" like Python slice)
    if job_range is not None:
        parts = job_range.split(':')
        if len(parts) == 2:
            r_start = int(parts[0]) if parts[0] else 0
            r_end = int(parts[1]) if parts[1] else len(jobs_to_run)
            jobs_to_run = jobs_to_run[r_start:r_end]
            print(f"  Job range filter: indices {r_start}:{r_end} → {len(jobs_to_run)} jobs selected")
        else:
            print(f"  [Warning] Invalid --job-range format '{job_range}' (expected 'start:end'). Ignoring.")

    total_jobs = len(df_manifest)
    queued_count = len(jobs_to_run)
    print(f"\nManifest Status: {total_jobs} total jobs | {queued_count} queued to run.")
    print(f"Already completed: {int((df_manifest['status'] == 'ok').sum())} jobs.")
    print(f"Already failed:    {int((df_manifest['status'] == 'failed').sum())} jobs (skipping unless --retry-failed).")

    if not jobs_to_run:
        print("\nAll jobs are already processed. Nothing to do!")
        return

    # Keep track of start time for the entire batch
    batch_start = time.time()

    if parallel_workers > 1:
        # ── Parallel execution via multiprocessing ──────────────────────
        import multiprocessing as mp
        mp.set_start_method('spawn', force=True)

        # Build job dicts for workers (only the data needed by _worker_run_job)
        job_dicts = [df_manifest.loc[ji].to_dict() for ji in jobs_to_run]

        # Mark all pending jobs as 'running' before dispatch
        for ji in jobs_to_run:
            df_manifest.at[ji, 'status'] = 'running'
            df_manifest.at[ji, 'timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_manifest_state(df_manifest)

        n_workers = min(parallel_workers, len(job_dicts))
        print(f"  Launching {n_workers} parallel workers for {len(job_dicts)} jobs...\n")

        with mp.Pool(processes=n_workers) as pool:
            # Use imap_unordered for responsiveness — results arrive as they complete
            for completed_idx, result in enumerate(pool.imap_unordered(_worker_run_job, job_dicts), 1):
                jid = result['job_id']
                # Find the manifest row for this job_id
                mask = df_manifest['job_id'] == jid
                if mask.any():
                    ji = df_manifest[mask].index[0]
                else:
                    continue

                # Update manifest with worker results
                for col in ['status', 'output_file', 'solar_fraction_pct', 'total_solar_kJ',
                             'total_aux_kJ', 'total_tes_discharge_kJ', 'convergence_errors',
                             'elapsed_seconds', 'error_message']:
                    if col in result:
                        df_manifest.at[ji, col] = result[col]

                sf = result.get('solar_fraction_pct', np.nan)
                elapsed = result.get('elapsed_seconds', 0)
                n_err = result.get('convergence_errors', np.nan)
                err_msg = result.get('error_message', '')
                status = result.get('status', 'failed')

                save_manifest_state(df_manifest)

                if no_progress:
                    sf_str = f"{sf:.1f}%" if not pd.isna(sf) else "N/A"
                    err_str = f"{int(n_err)}" if not pd.isna(n_err) else "—"
                    tag_str = f"[{status.upper()}]"
                    print(f"  [{completed_idx}/{len(job_dicts)}] {jid[:60]}... "
                          f"SF={sf_str}  Errors={err_str}  Time={elapsed:.0f}s  {tag_str}")
                else:
                    _print_dashboard(df_manifest, batch_start, job_dicts, completed_idx,
                                     jid, status, sf if not pd.isna(sf) else None,
                                     elapsed, int(n_err) if not pd.isna(n_err) else None,
                                     err_msg[:80] if status == 'failed' else None)

    else:
        # ── Sequential execution (original path, preserved as fallback) ──
        for idx, job_idx in enumerate(jobs_to_run, 1):
            job = df_manifest.loc[job_idx].to_dict()
            jid = job['job_id']
            
            if no_progress:
                print(f"\n[{idx}/{queued_count}] Running simulation: {jid}")
                print(f"  Params: Topology={job['topology']}, Tank Config={job['tank_config']}, HTF={job['htf']}, "
                      f"Aperture={job['aperture']} m2, D={job['tank_diameter']}m, H={job['tank_height']}m, "
                      f"dp={job['particle_diameter']:.3f}m, vf={job['void_fraction']:.2f}, ins={job['insulation_thickness']:.2f}")

            df_manifest.at[job_idx, 'status'] = 'running'
            df_manifest.at[job_idx, 'timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_manifest_state(df_manifest)

            t0 = time.time()
            try:
                run_id = generate_run_id(job)
                df_res, filename, meta = run_single_simulation(
                    days=int(job['days']),
                    topology=job['topology'],
                    tank_config=job['tank_config'],
                    htf=job['htf'],
                    tag=job['tag'],
                    aperture=float(job['aperture']),
                    tank_diameter=float(job['tank_diameter']),
                    tank_height=float(job['tank_height']),
                    particle_diameter=float(job['particle_diameter']),
                    void_fraction=float(job['void_fraction']),
                    insulation_thickness=float(job['insulation_thickness']),
                    run_id=run_id,
                    charge_margin=float(job.get('charge_margin', 1.5)),
                    mass_steel_per_hour=float(job['mass_steel_per_hour']) if 'mass_steel_per_hour' in job and job['mass_steel_per_hour'] is not None and not pd.isna(job['mass_steel_per_hour']) else None
                )

                sol_useful = df_res['solar_to_proc_kJ'].sum() + df_res['tes_to_proc_kJ'].sum()
                aux_proc = df_res['aux_to_proc_kJ'].sum()
                aux_tes = df_res['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in df_res.columns else 0.0
                total_aux = aux_proc + aux_tes
                total_demand = sol_useful + total_aux
                sf = (sol_useful / total_demand * 100.0) if total_demand > 0 else 0.0
                n_failed = int((df_res['iter_status'] == 'failed').sum()) if 'iter_status' in df_res.columns else 0
                elapsed = time.time() - t0

                df_manifest.at[job_idx, 'status'] = 'ok'
                df_manifest.at[job_idx, 'elapsed_seconds'] = round(elapsed, 1)
                df_manifest.at[job_idx, 'output_file'] = filename
                df_manifest.at[job_idx, 'solar_fraction_pct'] = round(sf, 2)
                df_manifest.at[job_idx, 'total_solar_kJ'] = round(sol_useful, 1)
                df_manifest.at[job_idx, 'total_aux_kJ'] = round(total_aux, 1)
                df_manifest.at[job_idx, 'total_tes_discharge_kJ'] = round(df_res['tes_to_proc_kJ'].sum(), 1)
                df_manifest.at[job_idx, 'convergence_errors'] = n_failed
                df_manifest.at[job_idx, 'error_message'] = ''

                if no_progress:
                    print(f"  [SUCCESS] Finished in {elapsed:.1f}s | Solar Fraction: {sf:.1f}% | Errors: {n_failed}")
                else:
                    _print_dashboard(df_manifest, batch_start, jobs_to_run, idx, jid,
                                     'ok', sf, elapsed, n_failed, None)

            except Exception as e:
                elapsed = time.time() - t0
                err_msg = str(e)
                df_manifest.at[job_idx, 'status'] = 'failed'
                df_manifest.at[job_idx, 'elapsed_seconds'] = round(elapsed, 1)
                df_manifest.at[job_idx, 'error_message'] = err_msg.replace('\n', ' ')

                if no_progress:
                    print(f"  [FAILED] Simulation failed in {elapsed:.1f}s: {err_msg}")
                else:
                    _print_dashboard(df_manifest, batch_start, jobs_to_run, idx, jid,
                                     'FAILED', None, elapsed, None, err_msg[:80])

            save_manifest_state(df_manifest)

    batch_elapsed = time.time() - batch_start
    print(f"\n{'#'*70}")
    print(f"  BATCH COMPLETED IN {batch_elapsed/3600:.2f} HOURS")
    print(f"{'#'*70}")

def print_manifest_summary():
    """Reads the current manifest from file and displays a clean summary table of results."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"No manifest file found at {MANIFEST_PATH}")
        return

    df = pd.read_csv(MANIFEST_PATH)
    total = len(df)
    ok = (df['status'] == 'ok').sum()
    failed = (df['status'] == 'failed').sum()
    pending = (df['status'] == 'pending').sum()

    print(f"\n{'='*70}")
    print(f"  SWEEP SUMMARY TABLE — {ok} succeeded | {failed} failed | {pending} pending")
    print(f"{'='*70}")

    if failed > 0:
        print("\nFailed runs:")
        for _, row in df[df['status'] == 'failed'].iterrows():
            print(f"  - {row['job_id']}: {row['error_message']}")

    print(f"\n  {'Job Label':<55} {'SF%':>6}  {'Aux_GJ':>8}  {'Status'}")
    print(f"  {'-'*76}")
    for _, row in df.iterrows():
        sf_val = row['solar_fraction_pct']
        sf_str = f"{sf_val:.1f}" if not pd.isna(sf_val) else "  N/A"
        aux_val = row['total_aux_kJ']
        aux_str = f"{aux_val/1e6:.2f}" if not pd.isna(aux_val) else "   N/A"
        
        # Truncate label for display
        label = row['job_id']
        if len(label) > 55:
            label = label[:52] + "..."
            
        print(f"  {label:<55} {sf_str:>6}  {aux_str:>8}  {row['status']}")
    print(f"\nSummary manifest file: {MANIFEST_PATH}")


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run a robust, resumable parametric sweep over PBTES design variables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sweep configurations:
  aperture       PTC aperture area: 500, 750, 1000, 1500, 2000, 3000 m²
  tes_volume     TES tank: D=[4,5,6,7,8,10] m × H=[3,4,5,6,8] m (30 points)
  topology       PI vs SD: Parallel/indirect vs Series/direct
  physical_sens  Sensitivity to rock size (dp), void fraction (vf), and insulation thickness
  htf            Primary NaK vs comparison Air loop baseline runs
  full           Combination of all sweeps above

Checkpoints:
  Checkpointing is stored in results/parametric_manifest.csv.
  If the simulation is interrupted, running the command again will resume
  automatically. To force restart, pass the --reset-manifest flag.
        """
    )
    parser.add_argument(
        '--sweep',
        type=str,
        default='topology',
        choices=['aperture', 'tes_volume', 'topology', 'physical_sens', 'htf', 'full'],
        help="Which parameter sweep to run (default: topology)."
    )
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help="Number of simulation days per sweep point (default: 365)."
    )
    parser.add_argument(
        '--tag',
        type=str,
        default='sweep',
        help="Tag prefix for results and manifest (default: 'sweep')."
    )
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help="Force rerun of previously failed jobs (default: skip failed)."
    )
    parser.add_argument(
        '--reset-manifest',
        action='store_true',
        help="Archive existing manifest and create a new one from scratch."
    )
    parser.add_argument(
        '--job-range',
        type=str,
        default=None,
        help="Process only a slice of pending jobs (format: 'start:end', Python slice notation)."
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help="Disable live dashboard (use plain text output — for logging or headless environments)."
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help="Number of parallel worker processes (default: 1 = sequential)."
    )
    
    args = parser.parse_args()

    print(f"\n{'#'*70}")
    print(f"  PBTES PARAMETRIC SWEEP ENGINE")
    print(f"  Sweep: {args.sweep}  |  Days: {args.days}  |  Tag: {args.tag}")
    print(f"  Restart checklist: results/parametric_manifest.csv")
    if args.job_range:
        print(f"  Job range: {args.job_range}")
    if args.no_progress:
        print(f"  Dashboard: disabled (plain text output)")
    if args.parallel > 1:
        print(f"  Parallel workers: {args.parallel}")
    print(f"{'#'*70}")

    # Run the sweeps loop
    execute_sweeps(
        sweep_type=args.sweep,
        days=args.days,
        tag=args.tag,
        retry_failed=args.retry_failed,
        reset_manifest=args.reset_manifest,
        job_range=args.job_range,
        no_progress=args.no_progress,
        parallel_workers=args.parallel
    )

    # Output summary results
    print_manifest_summary()

if __name__ == '__main__':
    main()
