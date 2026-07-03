"""
PBTES Full Parametric Sweep Dashboard
=====================================
Complete sweep grid for journal publication (Q1: JES / Energy / Solar Energy).
Covers all 5 sweep groups from PARAMETRIC_SWEEP_PLAN.md + SD extensions
for PI vs SD gap analysis + extended DxH for LCOH U-shape.

Grid: ~70 unique jobs x 365 days each
Parallel: up to 8 workers, multiprocessing.spawn
Estimated wall-clock: 12-15h at N=8

Usage:
    python scripts/sweep_dashboard.py     # opens tkinter GUI

The dashboard runs independently — close this terminal/agent after launching.
"""
import sys, os, time, threading, json, queue, multiprocessing as mp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.makedirs('results', exist_ok=True)

import tkinter as tk
from tkinter import ttk
import numpy as np

# ── Baseline parameters ────────────────────────────────────────────────────────
BL = {
    'topology': 'Parallel', 'tank_config': 'indirect', 'htf': 'INCOMP::NaK',
    'tag': 'pub', 'days': 365,
    'aperture': 1000.0, 'tank_diameter': 7.0, 'tank_height': 5.0,
    'particle_diameter': 0.050, 'void_fraction': 0.40, 'insulation_thickness': 1.0,
    'charge_margin': 1.5, 'mass_steel_per_hour': None
}

def _j(**overrides):
    j = BL.copy()
    j.update(overrides)
    tl = 'PI' if j['topology'] == 'Parallel' else 'SD'
    label = f"{tl} D={j['tank_diameter']:.0f} H={j['tank_height']:.0f} A={j['aperture']:.0f}"
    if abs(j['particle_diameter'] - 0.05) > 0.001:
        label += f" dp={j['particle_diameter']:.3f}"
    if abs(j['void_fraction'] - 0.40) > 0.005:
        label += f" vf={j['void_fraction']:.2f}"
    if abs(j['insulation_thickness'] - 1.0) > 0.01:
        label += f" ins={j['insulation_thickness']:.2f}"
    if abs(j['charge_margin'] - 1.5) > 0.01:
        label += f" cm={j['charge_margin']:.2f}"
    if j['mass_steel_per_hour'] is not None and abs(j['mass_steel_per_hour'] - 5000.0) > 1.0:
        label += f" msh={j['mass_steel_per_hour']:.0f}"
    if j['htf'] != 'INCOMP::NaK':
        label += " Air"
    j['label'] = label
    return j

JOBS = []
seen = set()

def _add(j):
    key = (j['topology'], j['tank_config'], j['htf'],
           j['aperture'], j['tank_diameter'], j['tank_height'],
           j['particle_diameter'], j['void_fraction'], j['insulation_thickness'],
           j.get('charge_margin', 1.5), j.get('mass_steel_per_hour'))
    if key not in seen:
        seen.add(key)
        JOBS.append(j)

# ═══════════════════════════════════════════════════════════════════════════════
#  Sweep A: Aperture Area (Solar Multiple) — PI + SD at baseline geometry (Group 1)
# ═══════════════════════════════════════════════════════════════════════════════
APERTURES = [500.0, 750.0, 1000.0, 1250.0, 1500.0, 1750.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 4500.0, 5000.0, 6000.0]
for A in APERTURES:
    _add(_j(aperture=A, topology='Parallel'))
    _add(_j(aperture=A, topology='Series', tank_config='direct'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Sweep B & C: Full D×H Geometrical Grid — PI & SD (Group 2 & 3)
# ═══════════════════════════════════════════════════════════════════════════════
grid_points = []
# Core grid: D=[4-8] × H=[3-8] (30 points)
for D in [4.0, 5.0, 6.0, 7.0, 8.0]:
    for H in [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
        grid_points.append((D, H))
# Medium grid: D=[9,10,12] × H=[4,5,6,8,10] (15 points)
for D in [9.0, 10.0, 12.0]:
    for H in [4.0, 5.0, 6.0, 8.0, 10.0]:
        grid_points.append((D, H))
# Large grid: D=[14,16] × H=[5,6,8,10,12] (10 points)
for D in [14.0, 16.0]:
    for H in [5.0, 6.0, 8.0, 10.0, 12.0]:
        grid_points.append((D, H))
# XLarge grid: D=[18,20] × H=[5,8,10,12] (8 points)
for D in [18.0, 20.0]:
    for H in [5.0, 8.0, 10.0, 12.0]:
        grid_points.append((D, H))

for D, H in grid_points:
    _add(_j(tank_diameter=D, tank_height=H, topology='Parallel'))
    _add(_j(tank_diameter=D, tank_height=H, topology='Series', tank_config='direct'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Sweep A×D×H Coupling — PI & SD (Group 4 & 5)
# ═══════════════════════════════════════════════════════════════════════════════
for A in [1500.0, 2000.0, 3000.0, 4000.0]:
    for D in [7.0, 10.0, 14.0]:
        for H in [5.0, 8.0, 12.0]:
            _add(_j(aperture=A, tank_diameter=D, tank_height=H, topology='Parallel'))
            _add(_j(aperture=A, tank_diameter=D, tank_height=H, topology='Series', tank_config='direct'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Sweep D: Physical Sensitivities — PI & SD at A=1000 and A=3000 (Group 6 & 7)
# ═══════════════════════════════════════════════════════════════════════════════
for A_sens in [1000.0, 3000.0]:
    # PI
    for dp in [0.030, 0.070, 0.100]:
        _add(_j(aperture=A_sens, particle_diameter=dp, topology='Parallel'))
    for vf in [0.35, 0.45]:
        _add(_j(aperture=A_sens, void_fraction=vf, topology='Parallel'))
    for ins in [0.50, 0.75, 1.25]:
        _add(_j(aperture=A_sens, insulation_thickness=ins, topology='Parallel'))
    # SD
    for dp in [0.030, 0.070, 0.100]:
        _add(_j(aperture=A_sens, particle_diameter=dp, topology='Series', tank_config='direct'))
    for vf in [0.35, 0.45]:
        _add(_j(aperture=A_sens, void_fraction=vf, topology='Series', tank_config='direct'))
    for ins in [0.50, 0.75, 1.25]:
        _add(_j(aperture=A_sens, insulation_thickness=ins, topology='Series', tank_config='direct'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Sweep E: HTF Comparison — Air at baseline + large geometry across apertures (Group 8)
# ═══════════════════════════════════════════════════════════════════════════════
AIR_APERTURES = [500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 5000.0]
for A in AIR_APERTURES:
    _add(_j(aperture=A, tank_diameter=7.0, tank_height=5.0, htf='Air', topology='Parallel'))
    _add(_j(aperture=A, tank_diameter=14.0, tank_height=10.0, htf='Air', topology='Parallel'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Group 9: UA Sizing & Exergoeconomic Sensitivities
# ═══════════════════════════════════════════════════════════════════════════════
for cm in [0.5, 0.8, 1.0, 1.2, 1.5]:
    for A in [1000.0, 3000.0]:
        _add(_j(aperture=A, charge_margin=cm, topology='Parallel'))
        _add(_j(aperture=A, charge_margin=cm, topology='Series', tank_config='direct'))

# ═══════════════════════════════════════════════════════════════════════════════
#  Group 10: Zinc Pool Production Mode Sensitivities
# ═══════════════════════════════════════════════════════════════════════════════
for msh in [2500.0, 7500.0]:
    for D in [5.0, 7.0, 10.0, 14.0]:
        _add(_j(tank_diameter=D, tank_height=5.0, mass_steel_per_hour=msh, topology='Parallel'))

N_JOBS = len(JOBS)
STATE_FILE = 'results/_dashboard_state.json'

# ── Test mode: filter to 8 representative jobs for quick validation ───────────
if '--test' in sys.argv:
    TEST_TUPLES = {
        ('Parallel', 500.0, 7.0, 5.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 1000.0, 7.0, 5.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 2000.0, 7.0, 5.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Series', 1000.0, 7.0, 5.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 1000.0, 4.0, 3.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 1000.0, 12.0, 8.0, 0.050, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 1000.0, 7.0, 5.0, 0.030, 0.40, 1.0, 'INCOMP::NaK'),
        ('Parallel', 1000.0, 7.0, 5.0, 0.050, 0.40, 1.0, 'Air'),
    }
    JOBS[:] = [j for j in JOBS
               if (j['topology'], j['aperture'], j['tank_diameter'], j['tank_height'],
                   j['particle_diameter'], j['void_fraction'], j['insulation_thickness'], j['htf']) in TEST_TUPLES]
    N_JOBS = len(JOBS)

print(f"Sweep grid: {N_JOBS} unique jobs")

# ── Module-level worker (required for mp.spawn pickling) ──────────────────────

def _mp_worker(job):
    t0 = time.time()
    idx = job['_idx']
    progress_file = f'results/_progress_{idx}.json'
    if os.path.exists(progress_file):
        os.remove(progress_file)
    try:
        from run_simulation import run_single_simulation
        from run_parametric import generate_run_id

        run_id = generate_run_id(job)
        df_res, fname, meta = run_single_simulation(
            days=job['days'], topology=job['topology'], tank_config=job['tank_config'],
            htf=job['htf'], tag=job['tag'], aperture=float(job['aperture']),
            tank_diameter=float(job['tank_diameter']), tank_height=float(job['tank_height']),
            particle_diameter=float(job['particle_diameter']),
            void_fraction=float(job['void_fraction']),
            insulation_thickness=float(job['insulation_thickness']),
            run_id=run_id, _progress_file=progress_file,
            charge_margin=float(job.get('charge_margin', 1.5)),
            mass_steel_per_hour=float(job['mass_steel_per_hour']) if 'mass_steel_per_hour' in job and job['mass_steel_per_hour'] is not None else None)

        elapsed = time.time() - t0
        sol = df_res['solar_to_proc_kJ'].sum() + df_res['tes_to_proc_kJ'].sum()
        aux = df_res['aux_to_proc_kJ'].sum()
        aux += df_res['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in df_res.columns else 0.0
        sf = sol / (sol + aux) * 100.0 if (sol + aux) > 0 else 0.0
        n_err = int((df_res['iter_status'] == 'failed').sum()) if 'iter_status' in df_res.columns else 0

        Q_ch = df_res['to_tes_kJ'].sum() / 1e6
        Q_dis = df_res['tes_to_proc_kJ'].sum() / 1e6
        Q_aux = aux / 1e6

        return {
            'idx': idx, 'status': 'ok', 'sf': round(sf, 1), 'elapsed': round(elapsed, 1),
            'errors': n_err, 'file': fname, 'error': '',
            'Q_charge_GJ': round(Q_ch, 2), 'Q_discharge_GJ': round(Q_dis, 2),
            'Q_aux_GJ': round(Q_aux, 2),
        }
    except Exception as e:
        return {
            'idx': idx, 'status': 'failed', 'sf': 0,
            'elapsed': round(time.time() - t0, 1),
            'errors': -1, 'file': '', 'error': str(e)[:200],
        }

# ── Shared state ──────────────────────────────────────────────────────────────
state_lock = threading.Lock()
state = {
    'running': False, 'start': 0, 'max_workers': 6,
    'jobs': [{'label': j['label'], 'status': 'pending', 'sf': None,
              'elapsed': 0, 'errors': 0, 'file': '',
              'Q_charge_GJ': None, 'Q_discharge_GJ': None, 'Q_aux_GJ': None}
             for j in JOBS],
}

def _write_state():
    with state_lock:
        data = {
            'running': state['running'], 'start': state['start'],
            'max_workers': state['max_workers'],
            'jobs': state['jobs'],
        }
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, default=str)

def _read_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
                with state_lock:
                    state['running'] = data.get('running', False)
                    state['start'] = data.get('start', 0)
                    state['max_workers'] = data.get('max_workers', 4)
                    for i, j in enumerate(data.get('jobs', [])):
                        if i < len(state['jobs']):
                            existing = state['jobs'][i]
                            if j.get('status') == 'ok' and existing.get('status') != 'ok':
                                existing.update(j)
                            elif j.get('status') == 'failed' and existing.get('status') not in ('ok',):
                                existing.update(j)
                            elif existing.get('status') == 'pending' and j.get('status') == 'running':
                                existing.update(j)
        except Exception:
            pass

# ── Pool manager (background thread) ──────────────────────────────────────────

class PoolManager:
    def __init__(self):
        self.pool = None
        self.pending = []
        self.active_count = 0
        self.results_queue = queue.Queue()
        self.submit_lock = threading.Lock()
        self.stop_flag = False
        self.thread = None

    def _on_result(self, result):
        self.results_queue.put(result)
        with self.submit_lock:
            self.active_count -= 1

    def start(self):
        self.stop_flag = False
        self.active_count = 0
        with state_lock:
            self.pending = [
                dict(JOBS[idx], _idx=idx)
                for idx, j in enumerate(state['jobs'])
                if j['status'] == 'pending'
            ]
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            pass
        max_w = state['max_workers']
        self.pool = mp.Pool(processes=max_w)

        while not self.stop_flag:
            max_w = state['max_workers']
            with self.submit_lock:
                while self.pending and self.active_count < max_w:
                    job = self.pending.pop(0)
                    idx = job['_idx']
                    with state_lock:
                        state['jobs'][idx]['status'] = 'running'
                    _write_state()
                    self.active_count += 1
                    self.pool.apply_async(_mp_worker, (job,), callback=self._on_result)

            with self.submit_lock:
                if not self.pending and self.active_count == 0:
                    break
            time.sleep(0.5)

        time.sleep(1)
        self.pool.close()
        self.pool.join()
        self.pool = None

    def stop(self):
        self.stop_flag = True
        if self.thread:
            self.thread.join(timeout=10)
        if self.pool:
            self.pool.terminate()
            self.pool.join()
            self.pool = None

# ── Tkinter GUI ───────────────────────────────────────────────────────────────

class Dashboard:
    def __init__(self, root):
        self.root = root
        root.title(f"PBTES Full Parametric Sweep — {N_JOBS} jobs x 365d")
        root.geometry("960x780")
        root.configure(bg='#1e1e1e')
        root.minsize(800, 500)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4', font=('Consolas', 9))
        style.configure('Header.TLabel', font=('Consolas', 12, 'bold'), foreground='#569cd6')
        style.configure('Ok.TLabel', foreground='#4ec9b0')
        style.configure('Fail.TLabel', foreground='#f44747')
        style.configure('Run.TLabel', foreground='#dcdcaa')
        style.configure('Pen.TLabel', foreground='#808080')
        style.configure('TFrame', background='#1e1e1e')
        style.configure('Small.TLabel', font=('Consolas', 8), foreground='#808080')

        self.manager = PoolManager()

        # ── Header ──
        frm = ttk.Frame(root)
        frm.pack(fill='x', padx=12, pady=(10, 4))
        ttk.Label(frm, text=f"PBTES FULL PARAMETRIC SWEEP — {N_JOBS} jobs", style='Header.TLabel').pack(side='left')
        self.status_lbl = ttk.Label(frm, text="Idle — Click Start to begin", style='Pen.TLabel')
        self.status_lbl.pack(side='right')

        # ── Controls ──
        ctrl = ttk.Frame(root)
        ctrl.pack(fill='x', padx=12, pady=2)
        ttk.Label(ctrl, text="Workers (1-8):").pack(side='left')
        self.worker_var = tk.IntVar(value=6)
        self.worker_spin = ttk.Spinbox(ctrl, from_=1, to=8, textvariable=self.worker_var, width=4,
                                       command=self._on_workers_changed)
        self.worker_spin.pack(side='left', padx=4)
        ttk.Label(ctrl, text="  Change anytime — gates next job launch").pack(side='left')
        self.btn = ttk.Button(ctrl, text=f"START SWEEP ({N_JOBS} x 365d, ~14h)", command=self.start)
        self.btn.pack(side='right')

        # ── Main progress ──
        frm2 = ttk.Frame(root)
        frm2.pack(fill='x', padx=12, pady=4)
        self.main_bar = ttk.Progressbar(frm2, mode='determinate')
        self.main_bar.pack(fill='x')
        self.main_lbl = ttk.Label(frm2, text=f"0 / {N_JOBS} jobs  |  ETA: --")
        self.main_lbl.pack(anchor='w')

        ttk.Separator(root, orient='horizontal').pack(fill='x', padx=12, pady=4)

        # ── Column headers ──
        hdr = ttk.Frame(root)
        hdr.pack(fill='x', padx=12)
        ttk.Label(hdr, text="  Job", width=22, anchor='w', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Progress", width=16, anchor='w', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="SF%", width=7, anchor='e', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Time", width=7, anchor='e', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Qch GJ", width=7, anchor='e', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Qdis GJ", width=7, anchor='e', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Err", width=5, anchor='e', style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text="Status", width=9, anchor='e', style='Header.TLabel').pack(side='left')

        # ── Scrollable job rows ──
        canvas_frame = ttk.Frame(root)
        canvas_frame.pack(fill='both', expand=True, padx=12, pady=2)

        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.rows_frame = ttk.Frame(self.canvas)

        self.rows_frame.bind('<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0, 0), window=self.rows_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.canvas.bind_all('<MouseWheel>',
            lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        # ── Build job rows ──
        self.row_widgets = {}
        for job in JOBS:
            rf = ttk.Frame(self.rows_frame)
            rf.pack(fill='x', pady=1)
            w = {
                'label': ttk.Label(rf, text=job['label'], width=22, anchor='w', font=('Consolas', 8)),
                'bar': ttk.Progressbar(rf, length=120, mode='determinate'),
                'sf': ttk.Label(rf, text="---", width=7, anchor='e', font=('Consolas', 8)),
                'time': ttk.Label(rf, text="---", width=7, anchor='e', font=('Consolas', 8)),
                'qch': ttk.Label(rf, text="---", width=7, anchor='e', font=('Consolas', 8)),
                'qdis': ttk.Label(rf, text="---", width=7, anchor='e', font=('Consolas', 8)),
                'err': ttk.Label(rf, text="...", width=5, anchor='e', font=('Consolas', 8)),
                'status': ttk.Label(rf, text="pending", width=9, anchor='e', font=('Consolas', 8)),
            }
            for key in ['label', 'bar', 'sf', 'time', 'qch', 'qdis', 'err', 'status']:
                w[key].pack(side='left', padx=1)
            self.row_widgets[job['label']] = w

        self.refresh()

    def _on_workers_changed(self):
        try:
            new_val = self.worker_var.get()
            if 1 <= new_val <= 8:
                with state_lock:
                    state['max_workers'] = new_val
        except Exception:
            pass

    def start(self):
        self.btn.config(state='disabled', text="Running...")
        self.worker_spin.config(state='normal')
        with state_lock:
            state['running'] = True
            state['start'] = time.time()
            state['max_workers'] = self.worker_var.get()
            # Recover from existing CSVs
            self._recover_from_csvs()
            # Reset stale 'running' -> 'pending'
            for idx, j in enumerate(state['jobs']):
                if j['status'] == 'running':
                    self._cleanup_stale(idx, j)
                    j['status'] = 'pending'
        _write_state()
        self.manager.start()
        self.refresh()

    def _cleanup_stale(self, idx, j):
        f = j.get('file', '')
        if f and os.path.exists(f):
            try: os.remove(f)
            except Exception: pass
        pf = f'results/_progress_{idx}.json'
        if os.path.exists(pf):
            try: os.remove(pf)
            except Exception: pass
        from run_parametric import generate_run_id
        try:
            run_id = generate_run_id(JOBS[idx])
            cache_dir = os.path.join('.tespy_cache', run_id)
            if os.path.isdir(cache_dir):
                import shutil
                shutil.rmtree(cache_dir, ignore_errors=True)
        except Exception: pass
        j['sf'] = None; j['elapsed'] = 0; j['errors'] = 0; j['file'] = ''

    def _recover_from_csvs(self):
        import glob as _g, pandas as _pd
        csvs = _g.glob('results/pub_*.csv')
        for csv_path in csvs:
            try:
                with open(csv_path, encoding='utf-8') as f:
                    first = f.readline()
                if not first.startswith('__meta__,'):
                    continue
                meta_str = first.replace('__meta__,', '').strip()
                meta = json.loads(meta_str)
                dims = meta.get('dimensions', {})
                sim_args = meta.get('sim_args', {})
                topo = meta.get('topology', '')
                A = dims.get('aperture_area', sim_args.get('aperture', 1000))
                D = dims.get('tank_diameter', 7)
                H = dims.get('tank_height', 5)
                dp_val = dims.get('particle_diameter', 0.05)
                vf_val = dims.get('void_fraction', 0.40)
                ins_val = dims.get('insulation_thickness', 1.0)
                htf_val = meta.get('HTF', 'INCOMP::NaK')
                cm_val = meta.get('charge_margin', 1.5)
                msh_val = meta.get('mass_steel_per_hour', 5000.0)
                for idx, job in enumerate(JOBS):
                    job_cm = job.get('charge_margin')
                    job_cm = job_cm if job_cm is not None else 1.5
                    job_msh = job.get('mass_steel_per_hour')
                    job_msh = job_msh if job_msh is not None else 5000.0
                    if (job['topology'] == topo and
                        abs(job['aperture'] - A) < 0.1 and
                        abs(job['tank_diameter'] - D) < 0.01 and
                        abs(job['tank_height'] - H) < 0.01 and
                        abs(job['particle_diameter'] - dp_val) < 0.001 and
                        abs(job['void_fraction'] - vf_val) < 0.005 and
                        abs(job['insulation_thickness'] - ins_val) < 0.01 and
                        job['htf'] == htf_val and
                        abs(job_cm - cm_val) < 0.01 and
                        abs(job_msh - msh_val) < 1.0):
                        j = state['jobs'][idx]
                        if j['status'] in ('ok',):
                            break
                        try:
                            df = _pd.read_csv(csv_path, skiprows=1)
                            sol = df['solar_to_proc_kJ'].sum() + df['tes_to_proc_kJ'].sum()
                            aux = df['aux_to_proc_kJ'].sum()
                            aux += df['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in df.columns else 0.0
                            sf = sol / (sol + aux) * 100.0 if (sol + aux) > 0 else 0.0
                            n_err = int((df['iter_status'] == 'failed').sum()) if 'iter_status' in df.columns else 0
                            Q_ch = df['to_tes_kJ'].sum() / 1e6
                            Q_dis = df['tes_to_proc_kJ'].sum() / 1e6
                            j['status'] = 'ok'; j['sf'] = round(sf, 1)
                            j['elapsed'] = meta.get('sim_args', {}).get('elapsed_seconds', 0)
                            j['errors'] = n_err; j['file'] = csv_path
                            j['Q_charge_GJ'] = round(Q_ch, 2)
                            j['Q_discharge_GJ'] = round(Q_dis, 2)
                            j['Q_aux_GJ'] = round(aux / 1e6, 2)
                        except Exception:
                            j['status'] = 'ok'; j['file'] = csv_path
                        break
            except Exception:
                pass

    def on_close(self):
        self.manager.stop()
        self.root.destroy()

    def refresh(self):
        _read_state()
        # Process results from pool
        while not self.manager.results_queue.empty():
            try:
                result = self.manager.results_queue.get_nowait()
                idx = result['idx']
                with state_lock:
                    if idx < len(state['jobs']):
                        j = state['jobs'][idx]
                        j['status'] = result['status']
                        j['sf'] = result.get('sf')
                        j['elapsed'] = result.get('elapsed', 0)
                        j['errors'] = result.get('errors', 0)
                        j['file'] = result.get('file', '')
                        j['Q_charge_GJ'] = result.get('Q_charge_GJ')
                        j['Q_discharge_GJ'] = result.get('Q_discharge_GJ')
                        j['Q_aux_GJ'] = result.get('Q_aux_GJ')
            except queue.Empty:
                break

        jobs_data = state['jobs']
        running = state['running']

        # Read per-job progress files
        job_progress = {}
        for idx in range(N_JOBS):
            pf = f'results/_progress_{idx}.json'
            if os.path.exists(pf):
                try:
                    with open(pf) as f:
                        d = json.load(f)
                        step = d.get('step', 0)
                        total = d.get('total', 168)
                        job_progress[idx] = (step / total * 100) if total > 0 else 0
                except Exception:
                    job_progress[idx] = 0
            elif jobs_data[idx]['status'] in ('ok', 'failed'):
                job_progress[idx] = 100
            else:
                job_progress[idx] = 0

        total_pct = sum(job_progress.values()) / N_JOBS if N_JOBS > 0 else 0
        self.main_bar['value'] = total_pct

        n_ok = sum(1 for j in jobs_data if j['status'] == 'ok')
        n_fail = sum(1 for j in jobs_data if j['status'] == 'failed')
        n_running = sum(1 for j in jobs_data if j['status'] == 'running')
        n_done = n_ok + n_fail

        elapsed = time.time() - state['start'] if running and state['start'] > 0 else 0
        completed = [j for j in jobs_data if j['elapsed'] > 0 and j['status'] in ('ok', 'failed')]
        avg_sec = sum(j['elapsed'] for j in completed) / len(completed) if completed else 90.0
        eta = ''
        if n_done > 0 and n_done < N_JOBS:
            remaining = N_JOBS - n_done
            eta_s = (remaining / state['max_workers']) * avg_sec
            if n_running > 0:
                eta_s = max(0, eta_s - avg_sec * 0.3)
            eta = f"ETA: {eta_s/60:.0f} min" if eta_s < 3600 else f"ETA: {eta_s/3600:.1f} h"
        el_str = f"{elapsed/60:.0f} min" if elapsed < 3600 else f"{elapsed/3600:.1f} h"
        self.main_lbl.config(
            text=f"{n_done} / {N_JOBS} jobs  |  {n_running} running (max {state['max_workers']})  |  "
                 f"Elapsed: {el_str}  |  {eta}  |  ok={n_ok} fail={n_fail}")

        if running:
            self.status_lbl.config(text=f"Running — {state['max_workers']} workers", style='Run.TLabel')
        elif n_fail > 0 and n_ok > 0:
            self.status_lbl.config(text=f"Done — {n_ok} ok, {n_fail} failed", style='Fail.TLabel')
        elif n_fail > 0:
            self.status_lbl.config(text=f"Done — ALL {n_fail} FAILED", style='Fail.TLabel')
        elif n_ok > 0:
            self.status_lbl.config(text=f"COMPLETE — {n_ok}/{N_JOBS} jobs ok", style='Ok.TLabel')
        else:
            self.status_lbl.config(text="Idle — Click Start to begin", style='Pen.TLabel')

        # Update per-job rows
        for idx, job in enumerate(JOBS):
            label = job['label']
            if label not in self.row_widgets:
                continue
            w = self.row_widgets[label]
            jd = jobs_data[idx]

            w['bar']['value'] = job_progress.get(idx, 0)

            if jd['sf'] is not None:
                sf = jd['sf']
                w['sf'].config(text=f"{sf:.1f}",
                               foreground='#4ec9b0' if sf > 50 else '#dcdcaa' if sf > 20 else '#f44747')
            elif jd['status'] == 'running':
                w['sf'].config(text="...", foreground='#808080')
            elif jd['status'] == 'failed':
                w['sf'].config(text="FAIL", foreground='#f44747')
            else:
                w['sf'].config(text="---", foreground='#808080')

            if jd['elapsed'] > 0:
                t = jd['elapsed']
                w['time'].config(text=f"{t/60:.0f}m" if t > 120 else f"{t:.0f}s")
            elif jd['status'] == 'running':
                w['time'].config(text="...")
            else:
                w['time'].config(text="---")

            if jd.get('Q_charge_GJ') is not None:
                w['qch'].config(text=f"{jd['Q_charge_GJ']:.1f}")
            else:
                w['qch'].config(text="---")

            if jd.get('Q_discharge_GJ') is not None:
                w['qdis'].config(text=f"{jd['Q_discharge_GJ']:.1f}")
            else:
                w['qdis'].config(text="---")

            if jd['status'] == 'ok':
                w['err'].config(text=str(jd['errors']),
                                foreground='#4ec9b0' if jd['errors'] == 0 else '#dcdcaa')
            elif jd['status'] == 'failed':
                w['err'].config(text="X", foreground='#f44747')
            else:
                w['err'].config(text="...", foreground='#808080')

            st = jd['status']
            if st == 'ok':
                w['status'].config(text="OK", foreground='#4ec9b0')
            elif st == 'running':
                w['status'].config(text="running", foreground='#dcdcaa')
            elif st == 'failed':
                w['status'].config(text="FAILED", foreground='#f44747')
            else:
                w['status'].config(text="pending", foreground='#808080')

        all_done = all(j['status'] in ('ok', 'failed') for j in jobs_data)
        if not running and all_done and n_ok > 0:
            self.btn.config(state='normal', text="Re-run Sweep")
        elif not running and not all_done and not self.manager.stop_flag:
            pass

        self.root.after(500, self.refresh)


def _classify_rq(job):
    """Map a job to the research question(s) it answers."""
    rqs = set()
    is_sd = job['topology'] == 'Series'
    A = job['aperture']; D = job['tank_diameter']; H = job['tank_height']
    dp = job['particle_diameter']; vf = job['void_fraction']
    ins = job['insulation_thickness']; htf = job['htf']
    is_baseline_geom = abs(D - 7.0) < 0.01 and abs(H - 5.0) < 0.01
    is_baseline_phys = abs(dp - 0.05) < 0.001 and abs(vf - 0.40) < 0.005 and abs(ins - 1.0) < 0.01
    is_baseline_A = abs(A - 1000.0) < 0.1
    if is_sd:
        rqs.add('RQ1')
    if is_baseline_geom and is_baseline_phys and htf == 'INCOMP::NaK':
        rqs.add('RQ2')
    if is_baseline_A and htf == 'INCOMP::NaK' and is_baseline_phys:
        rqs.add('RQ3')
    if not is_baseline_phys and htf == 'INCOMP::NaK':
        rqs.add('RQ4')
    if htf != 'INCOMP::NaK':
        rqs.add('HTF')
    if dp != 0.05 or (A >= 2000 and D <= 5):
        rqs.add('RQ5')
    if not is_baseline_A and not is_baseline_geom and is_baseline_phys and htf == 'INCOMP::NaK':
        rqs.add('RQ2')
        rqs.add('RQ3')
    return ','.join(sorted(rqs)) if rqs else 'RQ2'


def run_headless(n_workers=8):
    """Run the full sweep without tkinter GUI. Prints progress to console."""
    print(f"\n{'='*80}")
    print(f"PBTES PARAMETRIC SWEEP — HEADLESS MODE")
    print(f"Jobs: {N_JOBS} x 365 days | Workers: {n_workers}")
    est_cpu_h = N_JOBS * 1.5
    est_wall = est_cpu_h / n_workers
    print(f"Estimated: {est_cpu_h:.0f} CPU-h total, ~{est_wall:.0f}h wall-clock at N={n_workers}")
    print(f"{'='*80}\n")

    # Recover from existing CSVs
    state['running'] = True
    state['start'] = time.time()
    state['max_workers'] = n_workers

    # Inline CSV recovery
    import glob as _g, pandas as _pd
    csvs = _g.glob('results/pub_*.csv')
    recovered = 0
    for csv_path in csvs:
        try:
            with open(csv_path, encoding='utf-8') as f:
                first = f.readline()
            if not first.startswith('__meta__,'):
                continue
            meta_str = first.replace('__meta__,', '').strip()
            meta = json.loads(meta_str)
            dims = meta.get('dimensions', {})
            topo = meta.get('topology', '')
            A = dims.get('aperture_area', 1000)
            D = dims.get('tank_diameter', 7)
            H = dims.get('tank_height', 5)
            dp_val = dims.get('particle_diameter', 0.05)
            vf_val = dims.get('void_fraction', 0.40)
            ins_val = dims.get('insulation_thickness', 1.0)
            htf_val = meta.get('HTF', 'INCOMP::NaK')
            cm_val = meta.get('charge_margin', 1.5)
            msh_val = meta.get('mass_steel_per_hour', 5000.0)
            for idx, job in enumerate(JOBS):
                job_cm = job.get('charge_margin')
                job_cm = job_cm if job_cm is not None else 1.5
                job_msh = job.get('mass_steel_per_hour')
                job_msh = job_msh if job_msh is not None else 5000.0
                if (job['topology'] == topo and
                    abs(job['aperture'] - A) < 0.1 and
                    abs(job['tank_diameter'] - D) < 0.01 and
                    abs(job['tank_height'] - H) < 0.01 and
                    abs(job['particle_diameter'] - dp_val) < 0.001 and
                    abs(job['void_fraction'] - vf_val) < 0.005 and
                    abs(job['insulation_thickness'] - ins_val) < 0.01 and
                    job['htf'] == htf_val and
                    abs(job_cm - cm_val) < 0.01 and
                    abs(job_msh - msh_val) < 1.0):
                    j = state['jobs'][idx]
                    if j['status'] == 'ok':
                        break
                    try:
                        df = _pd.read_csv(csv_path, skiprows=1)
                        sol = df['solar_to_proc_kJ'].sum() + df['tes_to_proc_kJ'].sum()
                        aux = df['aux_to_proc_kJ'].sum()
                        aux += df['aux_tes_energy_kJ'].sum() if 'aux_tes_energy_kJ' in df.columns else 0.0
                        sf = sol / (sol + aux) * 100.0 if (sol + aux) > 0 else 0.0
                        n_err = int((df['iter_status'] == 'failed').sum()) if 'iter_status' in df.columns else 0
                        j['status'] = 'ok'; j['sf'] = round(sf, 1)
                        j['elapsed'] = meta.get('sim_args', {}).get('elapsed_seconds', 0)
                        j['errors'] = n_err; j['file'] = csv_path
                        j['Q_charge_GJ'] = round(df['to_tes_kJ'].sum() / 1e6, 2)
                        j['Q_discharge_GJ'] = round(df['tes_to_proc_kJ'].sum() / 1e6, 2)
                        j['Q_aux_GJ'] = round(aux / 1e6, 2)
                        recovered += 1
                    except Exception:
                        j['status'] = 'ok'; j['file'] = csv_path
                    break
        except Exception:
            pass
    if recovered > 0:
        print(f"Recovered {recovered} jobs from existing CSVs.\n")

    _write_state()

    # Build pending queue
    manager = PoolManager()
    manager.start()

    # Monitor loop
    last_done = 0
    while True:
        time.sleep(5)
        _read_state()
        # Drain results queue
        while not manager.results_queue.empty():
            try:
                result = manager.results_queue.get_nowait()
                idx = result['idx']
                with state_lock:
                    if idx < len(state['jobs']):
                        j = state['jobs'][idx]
                        j['status'] = result['status']
                        j['sf'] = result.get('sf')
                        j['elapsed'] = result.get('elapsed', 0)
                        j['errors'] = result.get('errors', 0)
                        j['file'] = result.get('file', '')
                        j['Q_charge_GJ'] = result.get('Q_charge_GJ')
                        j['Q_discharge_GJ'] = result.get('Q_discharge_GJ')
                        j['Q_aux_GJ'] = result.get('Q_aux_GJ')
            except queue.Empty:
                break
        _write_state()

        jobs_data = state['jobs']
        n_ok = sum(1 for j in jobs_data if j['status'] == 'ok')
        n_fail = sum(1 for j in jobs_data if j['status'] == 'failed')
        n_running = sum(1 for j in jobs_data if j['status'] == 'running')
        n_done = n_ok + n_fail
        n_pending = N_JOBS - n_done - n_running

        if n_done != last_done:
            last_done = n_done
            elapsed = time.time() - state['start']
            completed = [j for j in jobs_data if j['elapsed'] > 0 and j['status'] in ('ok', 'failed')]
            avg_sec = sum(j['elapsed'] for j in completed) / len(completed) if completed else 90.0
            remaining = N_JOBS - n_done
            eta_s = (remaining / n_workers) * avg_sec if remaining > 0 else 0
            el_str = f"{elapsed/60:.0f}m" if elapsed < 3600 else f"{elapsed/3600:.1f}h"
            eta_str = f"{eta_s/60:.0f}m" if eta_s < 3600 else f"{eta_s/3600:.1f}h"
            print(f"[{n_done}/{N_JOBS}] ok={n_ok} fail={n_fail} running={n_running} "
                  f"pending={n_pending} | elapsed={el_str} ETA={eta_str} "
                  f"avg={avg_sec:.0f}s/job")
            # Print latest completed jobs
            for idx in range(N_JOBS):
                j = jobs_data[idx]
                if j['status'] in ('ok', 'failed') and j['elapsed'] > 0:
                    pass  # Could print details here
            sys.stdout.flush()

        if n_done >= N_JOBS or (not state['running'] and n_running == 0 and manager.stop_flag):
            break

    manager.stop()
    state['running'] = False
    _write_state()

    # Final summary
    print(f"\n{'='*80}")
    print(f"SWEEP COMPLETE — {n_ok}/{N_JOBS} ok, {n_fail} failed")
    elapsed = time.time() - state['start']
    print(f"Total elapsed: {elapsed/3600:.1f}h")
    print(f"\nResults saved to results/pub_*.csv")
    print(f"State: {STATE_FILE}")
    print(f"{'='*80}")

    # Save summary
    summary = {
        'total_jobs': N_JOBS, 'ok': n_ok, 'failed': n_fail,
        'elapsed_hours': round(elapsed / 3600, 2),
        'jobs': [],
    }
    for idx, job in enumerate(JOBS):
        j = state['jobs'][idx]
        summary['jobs'].append({
            'idx': idx, 'label': job['label'],
            'topology': job['topology'], 'aperture': job['aperture'],
            'D': job['tank_diameter'], 'H': job['tank_height'],
            'dp': job['particle_diameter'], 'vf': job['void_fraction'],
            'ins': job['insulation_thickness'], 'htf': job['htf'],
            'rq': _classify_rq(job),
            'status': j['status'], 'sf': j.get('sf'),
            'file': j.get('file', ''),
        })
    with open('results/_sweep_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Summary: results/_sweep_summary.json")


if __name__ == '__main__':
    if '--headless' in sys.argv:
        nw = 6
        for i, a in enumerate(sys.argv):
            if a == '--workers' and i + 1 < len(sys.argv):
                nw = int(sys.argv[i + 1])
        run_headless(n_workers=nw)
    else:
        root = tk.Tk()
        app = Dashboard(root)
        root.mainloop()
