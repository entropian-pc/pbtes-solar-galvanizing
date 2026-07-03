"""
Assessment 06 -- Publication-Quality Figures
=============================================
Generates all article figures from aggregated parametric metrics and
individual simulation result CSVs.

Data sources:
  - results/parametric_metrics.csv  (aggregate metrics, one row per run)
  - results/*.csv                    (individual time-series for detailed figures)
  - TMY.csv                          (weather data)

Output: article_results/06_figures/ (*.svg + *.pdf)

Usage:
    python scripts/run_assessment_06_figures.py
    python scripts/run_assessment_06_figures.py --figures 8,9,10,11,12  # specific figures
    python scripts/run_assessment_06_figures.py --metrics results/parametric_metrics.csv

Figure inventory (17 total per PARAMETRIC_SWEEP_PLAN.md):
  01  Plant schematic (PI + SD)          -- skipped (manual diagram)
  02  Annual DNI + T_amb profile          -- TMY.csv
  03  TES temperature colormap            -- baseline CSV (needs >=30d)
  04  Summer week profile                 -- baseline CSV
  05  Winter week profile                 -- baseline CSV
  06  Monthly energy breakdown            -- baseline CSV (needs >=30d)
  07  Zinc pool temperature (year)        -- baseline CSV
  08  PI vs SD SF comparison              -- metrics (topology)
  09  SF vs aperture area                 -- metrics (aperture sweep)
  10  LCOH vs aperture area               -- metrics (aperture + economics)
  11  SF contour (D x H)                  -- metrics (TES volume sweep)
  12  LCOH contour (D x H)                -- metrics (TES volume + economics)
  13  Sensitivity tornado                 -- metrics (physical sens sweep)
  14  HTF comparison (NaK vs Air)         -- metrics (htf sweep) or skip
  15  Mode transition heatmap             -- baseline CSV
  16  Round-trip efficiency vs SM         -- metrics (aperture sweep)
  17  LCOH vs SF Pareto front             -- metrics (all sweeps)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from scipy.interpolate import griddata

from pbtes.analysis.results_reader import load_results

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'article_results')
FIG_DIR = os.path.join(BASE_DIR, '06_figures')
METRICS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'results', 'parametric_metrics.csv')
TMY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'TMY.csv')
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')

os.makedirs(FIG_DIR, exist_ok=True)

# ─── Journal-quality matplotlib defaults ──────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 13,
    'axes.titlesize': 13,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 10,
    'figure.dpi': 300,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

SKIPPED = {}
GENERATED_FIGS = set()


def _save(fig, name):
    fig.savefig(os.path.join(FIG_DIR, f'{name}.svg'), format='svg')
    fig.savefig(os.path.join(FIG_DIR, f'{name}.pdf'), format='pdf')
    plt.close(fig)


def _skip(fig_num, reason=''):
    SKIPPED[fig_num] = reason


# ─── Data loading helpers ─────────────────────────────────────────────

def load_metrics(filepath: str = None) -> pd.DataFrame:
    """Load the parametric metrics CSV. Returns empty DataFrame if not found."""
    fp = filepath or METRICS_PATH
    if not os.path.exists(fp):
        return pd.DataFrame()
    return pd.read_csv(fp)


def find_baseline_csv(topology='Parallel', prefer_days=365) -> str:
    """Find the best baseline CSV for a given topology. Strongly prefers 365d runs."""
    candidates = []
    if os.path.isdir(RESULTS_DIR):
        for f in os.listdir(RESULTS_DIR):
            if not f.endswith('.csv'):
                continue
            if '_processed' in f or '_exergo' in f or 'manifest' in f or 'metrics' in f:
                continue
            if 'archive' in f.lower():
                continue
            fp = os.path.join(RESULTS_DIR, f)
            candidates.append(fp)

    scored = []
    for fp in candidates:
        bn = os.path.basename(fp).lower()
        score = 0
        if topology.lower() in bn:
            score += 10
        # Heavily prefer 365d over 7d
        if '365d' in bn:
            score += 100
        elif '7d' in bn:
            score -= 50
        if 'baseline' in bn or 'curated' in bn:
            score += 3
        if '_a1000_' in bn:
            score += 2
        if 'd7.0' in bn and 'h5.0' in bn:
            score += 1
        if 'dp0.050' not in bn and 'vf0.40' not in bn:
            score -= 2
        try:
            size = os.path.getsize(fp)
            score += min(size / 50000, 2)
        except Exception:
            pass
        scored.append((score, fp))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else ''


# ═══════════════════════════════════════════════════════════════════════
# FIGURE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

# ── Fig 02: Annual DNI + T_amb profile ────────────────────────────────
def fig02_weather():
    if not os.path.exists(TMY_PATH):
        _skip('02', 'TMY.csv not found')
        return
    weather = pd.read_csv(TMY_PATH)
    if 'Fecha/Hora' not in weather.columns:
        _skip('02', 'TMY.csv missing Fecha/Hora column')
        return

    weather['time'] = pd.to_datetime(weather['Fecha/Hora'], errors='coerce')
    weather = weather.dropna(subset=['time']).sort_values('time')

    n_days = min(len(weather) // 24, 365)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    ax1.fill_between(weather['time'].iloc[:n_days*24],
                     weather['dni'].iloc[:n_days*24],
                     alpha=0.5, color='orange', linewidth=0)
    ax1.set_ylabel(r'DNI (W/m$^2$)')
    ax1.set_title('Annual Direct Normal Irradiance')

    ax2.plot(weather['time'].iloc[:n_days*24],
             weather['temp'].iloc[:n_days*24],
             color='royalblue', linewidth=0.5)
    ax2.set_ylabel(r'$T_{amb}$ (\N{DEGREE SIGN}C)')
    ax2.set_title('Ambient Temperature')
    ax2.set_xlabel('Date')

    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, 'fig02_weather')


# ── Fig 03: TES temperature colormap ─────────────────────────────────
def fig03_tes_colormap():
    fp = find_baseline_csv('Parallel', prefer_days=365)
    if not fp:
        fp = find_baseline_csv('Parallel', prefer_days=7)
    if not fp:
        _skip('03', 'no baseline CSV found')
        return

    try:
        df, meta = load_results(fp)
    except Exception as e:
        _skip('03', f'load error: {e}')
        return

    days = meta.get('sim_args', {}).get('days', 7)
    if days < 7:
        _skip('03', f'only {days}d data, need >=7d')
        return

    if 'tes_profile' not in df.columns or 'time' not in df.columns:
        _skip('03', 'missing tes_profile or time column')
        return

    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time', 'tes_profile'])

    # Parse temperature profiles from JSON
    profiles = []
    for _, row in df.iterrows():
        tp = row['tes_profile']
        if isinstance(tp, str):
            try:
                tp = json.loads(tp)
            except Exception:
                tp = []
        if isinstance(tp, (list, np.ndarray)) and len(tp) > 0:
            profiles.append(np.array(tp, dtype=float))

    if len(profiles) < 10:
        _skip('03', 'not enough tes_profile data')
        return

    # Stack into matrix: rows = time, cols = axial position
    n_times = len(profiles)
    n_nodes = min(len(p) for p in profiles)
    T_matrix = np.array([p[:n_nodes] for p in profiles])

    times = df['time'].values[:n_times]
    z_frac = np.linspace(0, 1, n_nodes)

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.pcolormesh(times, z_frac, T_matrix.T, shading='auto', cmap='plasma')
    cb = fig.colorbar(im, ax=ax, label=r'Temperature (\N{DEGREE SIGN}C)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Axial position (z/H)')
    ax.set_title(f'TES Temperature Profile — {days}d ({os.path.basename(fp)[:50]}...)')
    ax.invert_yaxis()
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, 'fig03_tes_colormap')


# ── Fig 04: Summer week profile ──────────────────────────────────────
# ── Fig 05: Winter week profile ──────────────────────────────────────
def _seasonal_week(df, meta, season='summer', fig_num='04'):
    """Plot a seasonal week profile: DNI, modes, TES temps, SoC."""
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time')

    if len(df) < 7 * 24:
        _skip(f'fig{fig_num}', f'not enough data for {season} week')
        return

    month = df['time'].dt.month
    if season == 'summer':
        # Southern hemisphere: Dec-Feb
        mask = month.isin([12, 1, 2])
    else:
        # Winter: Jun-Aug
        mask = month.isin([6, 7, 8])

    seasonal = df[mask]
    if len(seasonal) < 7 * 24:
        # Fallback: use any 7-day window
        seasonal = df.iloc[:7*24]

    # Take a representative 7-day slice
    start_idx = 0
    for i in range(len(seasonal) - 7*24):
        window = seasonal.iloc[i:i+7*24]
        if window['E'].mean() > 0:
            start_idx = i
            break
    week = seasonal.iloc[start_idx:start_idx + 7*24].copy()
    if len(week) < 24:
        _skip(f'fig{fig_num}', f'not enough {season} data')
        return

    times = week['time'].values

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

    # Panel 1: DNI
    ax = axes[0]
    ax.fill_between(times, week['E'].values, alpha=0.5, color='orange', linewidth=0)
    ax.set_ylabel(r'DNI (W/m$^2$)')
    ax.set_title(f'{season.title()} Week — DNI Profile')
    ax.set_ylim(bottom=0)

    # Panel 2: Operating Mode
    ax = axes[1]
    if 'TESmode' in week.columns:
        modes = week['TESmode'].astype(float).values
        ax.step(times, modes, where='mid', color='teal', linewidth=1.5)
        ax.set_ylabel('Mode')
        ax.set_title('Operating Mode')
        ax.set_yticks(sorted(set(int(m) for m in modes if not np.isnan(m))))
        ax.set_ylim(0, 7)
    else:
        ax.text(0.5, 0.5, 'No mode data', transform=ax.transAxes, ha='center')

    # Panel 3: TES temperatures
    ax = axes[2]
    if 'T_tes_top' in week.columns:
        ax.plot(times, week['T_tes_top'], color='crimson', linewidth=0.8, label='TES Top')
    if 'T_tes_bottom' in week.columns:
        ax.plot(times, week['T_tes_bottom'], color='royalblue', linewidth=0.8, label='TES Bottom')
    ax.set_ylabel(r'Temperature (\N{DEGREE SIGN}C)')
    ax.set_title('TES Temperatures')
    ax.legend(loc='upper right', framealpha=0.8)

    # Panel 4: SoC
    ax = axes[3]
    if 'tes_soc_kWh' in week.columns:
        ax.fill_between(times, week['tes_soc_kWh'].values, alpha=0.4, color='purple', linewidth=0)
        ax.set_ylabel('SoC (kWh)')
        ax.set_title('TES State of Charge')
    else:
        ax.text(0.5, 0.5, 'No SoC data', transform=ax.transAxes, ha='center')

    ax.set_xlabel('Date')
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, f'fig{fig_num}_{season}_week')


def fig04_summer_week():
    fp = find_baseline_csv('Parallel')
    if not fp:
        _skip('04', 'no baseline CSV')
        return
    df, meta = load_results(fp)
    _seasonal_week(df, meta, 'summer', '04')


def fig05_winter_week():
    fp = find_baseline_csv('Parallel')
    if not fp:
        _skip('05', 'no baseline CSV')
        return
    df, meta = load_results(fp)
    _seasonal_week(df, meta, 'winter', '05')


# ── Fig 06: Monthly energy breakdown ─────────────────────────────────
def fig06_monthly_energy():
    fp = find_baseline_csv('Parallel', prefer_days=365)
    if not fp:
        fp = find_baseline_csv('Parallel', prefer_days=7)
    if not fp:
        _skip('06', 'no baseline CSV')
        return

    df, meta = load_results(fp)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')

    days = meta.get('sim_args', {}).get('days', 7)
    if days < 30:
        # Group by day for short runs
        df['period'] = df['time'].dt.day
        period_label = 'Day'
    else:
        df['period'] = df['time'].dt.month
        period_label = 'Month'

    periods = sorted(df['period'].dropna().unique())
    if len(periods) < 2:
        _skip('06', 'not enough periods')
        return

    solar = []
    tes = []
    aux = []
    labels = []
    for p in periods:
        sub = df[df['period'] == p]
        solar.append(sub['solar_to_proc_kJ'].sum() / 1e6)
        tes.append(sub['tes_to_proc_kJ'].sum() / 1e6)
        aux.append(sub['aux_to_proc_kJ'].sum() / 1e6)
        labels.append(str(int(p)))

    x = np.arange(len(periods))
    width = 0.6

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x, solar, width, label='Solar Direct', color='gold', edgecolor='k', linewidth=0.3)
    ax.bar(x, tes, width, bottom=solar, label='TES Discharge', color='crimson', edgecolor='k', linewidth=0.3)
    bottom2 = np.array(solar) + np.array(tes)
    ax.bar(x, aux, width, bottom=bottom2, label='Auxiliary', color='grey', edgecolor='k', linewidth=0.3)

    ax.set_xlabel(period_label)
    ax.set_ylabel('Energy (GJ)')
    ax.set_title(f'Energy Breakdown by {period_label} — {os.path.basename(fp)[:60]}')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 10 else 0)
    ax.legend(loc='upper right', framealpha=0.8)
    fig.tight_layout()
    _save(fig, 'fig06_monthly_energy')


# ── Fig 07: Zinc pool temperature ────────────────────────────────────
def fig07_zinc_pool():
    fp = find_baseline_csv('Parallel')
    if not fp:
        _skip('07', 'no baseline CSV')
        return

    df, meta = load_results(fp)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time'])

    if 'T_zinc' not in df.columns:
        _skip('07', 'no T_zinc column')
        return

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df['time'], df['T_zinc'], color='darkorange', linewidth=0.6)
    ax.axhline(y=450, color='grey', linestyle='--', alpha=0.5, label='Min operating T')
    ax.set_ylabel(r'Zinc Pool Temperature (\N{DEGREE SIGN}C)')
    ax.set_title('Zinc Pool Temperature')
    ax.legend(loc='upper right')
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, 'fig07_zinc_pool')


# ── Fig 08: PI vs SD SF ──────────────────────────────────────────────
def fig08_topology_sf(metrics: pd.DataFrame):
    """SD vs PI: SF comparison + gap vs volume at A=1000."""
    df = metrics.copy()
    if df.empty:
        _skip('08', 'no metrics data')
        return

    a1000 = df[(df['aperture_m2'].between(990, 1010)) & (df['days'] >= 30)].dropna(
        subset=['sf_thermal_pct', 'tes_volume_m3'])
    if a1000.empty or a1000['topology'].nunique() < 2:
        _skip('08', 'need both PI and SD at A=1000')
        return

    pi = a1000[a1000['topology'].str.lower() == 'parallel'].sort_values('tes_volume_m3')
    sd = a1000[a1000['topology'].str.lower() == 'series'].sort_values('tes_volume_m3')

    # Merge on volume (approximate)
    vols = sorted(set(pi['tes_volume_m3'].round(-1)).union(set(sd['tes_volume_m3'].round(-1))))
    pi_sf = []; sd_sf = []; gaps = []
    for v in vols:
        p = pi.iloc[(pi['tes_volume_m3'] - v).abs().argsort()[:1]]
        s = sd.iloc[(sd['tes_volume_m3'] - v).abs().argsort()[:1]]
        if not p.empty and not s.empty:
            pi_sf.append(p['sf_thermal_pct'].values[0])
            sd_sf.append(s['sf_thermal_pct'].values[0])
            gaps.append(s['sf_thermal_pct'].values[0] - p['sf_thermal_pct'].values[0])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: SF vs volume
    ax1.plot(pi['tes_volume_m3'], pi['sf_thermal_pct'], 'o-', color='steelblue', label='PI', markersize=5)
    ax1.plot(sd['tes_volume_m3'], sd['sf_thermal_pct'], 's-', color='crimson', label='SD', markersize=5)
    ax1.set_xlabel('TES Volume (m$^3$)')
    ax1.set_ylabel('Solar Fraction (%)')
    ax1.set_title('PI vs SD — SF vs Tank Volume (A=1000 m$^2$)')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)

    # Right: SD-PI gap
    ax2.fill_between(vols, gaps, alpha=0.3, color='purple')
    ax2.plot(vols, gaps, 'D-', color='purple', markersize=6, linewidth=2)
    ax2.set_xlabel('TES Volume (m$^3$)')
    ax2.set_ylabel('SD - PI Gap (pp)')
    ax2.set_title(r'$\Delta$SF = SF$_{SD}$ - SF$_{PI}$ vs Tank Volume')
    ax2.axhline(y=0, color='grey', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    _save(fig, 'fig08_topology_sf')


# ── Fig 09: SF vs aperture area ──────────────────────────────────────
def fig09_sf_vs_aperture(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('09', 'no metrics data')
        return

    # Filter to baseline TES geometry
    geo = df[
        (df['tank_diameter_m'].between(6.9, 7.1)) &
        (df['tank_height_m'].between(4.9, 5.1))
    ]
    if len(geo) < 3:
        # Try wider tolerance
        geo = df[
            (df['tank_diameter_m'] > 6.5) &
            (df['tank_diameter_m'] < 7.5) &
            (df['tank_height_m'] > 4.5) &
            (df['tank_height_m'] < 5.5)
        ]

    unique_apertures = geo.dropna(subset=['sf_thermal_pct'])
    if len(unique_apertures) < 3:
        _skip('09', f'only {len(unique_apertures)} aperture points')
        return

    fig, ax = plt.subplots(figsize=(7, 5))

    for topo in unique_apertures['topology'].unique():
        sub = unique_apertures[unique_apertures['topology'] == topo]
        sub = sub.sort_values('aperture_m2')
        ax.plot(sub['aperture_m2'], sub['sf_thermal_pct'],
                'o-', label=topo, markersize=8, linewidth=2)

    ax.set_xlabel('PTC Aperture Area (m$^2$)')
    ax.set_ylabel('Solar Fraction (%)')
    ax.set_title('Solar Fraction vs Aperture Area')
    ax.legend(loc='lower right')

    # Add solar multiple on secondary axis
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2_ticks = ax.get_xticks()
    ax2.set_xticks(ax2_ticks)
    ax2.set_xticklabels([f'{t/1000:.1f}' for t in ax2_ticks])
    ax2.set_xlabel('Solar Multiple (SM)')

    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save(fig, 'fig09_sf_vs_aperture')


# ── Fig 10: LCOH vs aperture area ────────────────────────────────────
def fig10_lcoh_vs_aperture(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('10', 'no metrics data')
        return

    lcoh_ok = df.dropna(subset=['lcoh_usd_per_MWh'])
    if lcoh_ok.empty:
        _skip('10', 'no LCOH data (run with --skip-economics=False in aggregate)')
        return

    geo = lcoh_ok[
        (lcoh_ok['tank_diameter_m'].between(6.9, 7.1)) &
        (lcoh_ok['tank_height_m'].between(4.9, 5.1))
    ]
    if len(geo) < 3:
        geo = lcoh_ok

    fig, ax = plt.subplots(figsize=(7, 5))

    for topo in geo['topology'].unique():
        sub = geo[geo['topology'] == topo].sort_values('aperture_m2')
        ax.plot(sub['aperture_m2'], sub['lcoh_usd_per_MWh'],
                's-', label=topo, markersize=8, linewidth=2)

    ax.set_xlabel('PTC Aperture Area (m$^2$)')
    ax.set_ylabel('LCOH (USD/MWh)')
    ax.set_title('LCOH vs Aperture Area')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2_ticks = ax.get_xticks()
    ax2.set_xticks(ax2_ticks)
    ax2.set_xticklabels([f'{t/1000:.1f}' for t in ax2_ticks])
    ax2.set_xlabel('Solar Multiple (SM)')

    fig.tight_layout()
    _save(fig, 'fig10_lcoh_vs_aperture')


# ── Fig 11: SF contour (D x H) ───────────────────────────────────────
def fig11_sf_contour(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('11', 'no metrics data')
        return

    # Filter to PI topology, A=1000
    vol = df[
        (df['topology'].str.lower() == 'parallel') &
        (df['aperture_m2'].between(990, 1010))
    ]
    if len(vol) < 6:
        vol = df[(df['aperture_m2'].between(990, 1010))]

    vol = vol.dropna(subset=['tank_diameter_m', 'tank_height_m', 'sf_thermal_pct'])
    if len(vol) < 6:
        _skip('11', f'only {len(vol)} DxH points (need >=6)')
        return

    D_vals = vol['tank_diameter_m'].values
    H_vals = vol['tank_height_m'].values
    SF = vol['sf_thermal_pct'].values

    Di = np.linspace(D_vals.min(), D_vals.max(), 80)
    Hi = np.linspace(H_vals.min(), H_vals.max(), 80)
    Dg, Hg = np.meshgrid(Di, Hi)
    SFi = griddata((D_vals, H_vals), SF, (Dg, Hg), method='cubic')

    fig, ax = plt.subplots(figsize=(7, 5.5))
    cs = ax.contourf(Dg, Hg, SFi, levels=15, cmap='plasma')
    ax.scatter(D_vals, H_vals, c='white', edgecolor='k', s=40, zorder=5, linewidth=0.5)
    cb = fig.colorbar(cs, ax=ax, label='Solar Fraction (%)')
    ax.set_xlabel('Tank Diameter (m)')
    ax.set_ylabel('Tank Height (m)')
    ax.set_title('Solar Fraction vs Tank Geometry (PI, A=1000 m$^2$)')
    fig.tight_layout()
    _save(fig, 'fig11_sf_contour')


# ── Fig 12: LCOH contour (D x H) ─────────────────────────────────────
def fig12_lcoh_contour(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('12', 'no metrics data')
        return

    lcoh_ok = df.dropna(subset=['lcoh_usd_per_MWh', 'tank_diameter_m', 'tank_height_m'])
    if lcoh_ok.empty:
        _skip('12', 'no LCOH data')
        return

    vol = lcoh_ok[
        (lcoh_ok['topology'].str.lower() == 'parallel') &
        (lcoh_ok['aperture_m2'].between(990, 1010))
    ]
    if len(vol) < 6:
        vol = lcoh_ok[lcoh_ok['aperture_m2'].between(990, 1010)]

    if len(vol) < 6:
        _skip('12', f'only {len(vol)} DxH LCOH points')
        return

    D_vals = vol['tank_diameter_m'].values
    H_vals = vol['tank_height_m'].values
    LCOH = vol['lcoh_usd_per_MWh'].values

    Di = np.linspace(D_vals.min(), D_vals.max(), 80)
    Hi = np.linspace(H_vals.min(), H_vals.max(), 80)
    Dg, Hg = np.meshgrid(Di, Hi)
    LCOHi = griddata((D_vals, H_vals), LCOH, (Dg, Hg), method='cubic')

    fig, ax = plt.subplots(figsize=(7, 5.5))
    cs = ax.contourf(Dg, Hg, LCOHi, levels=15, cmap='viridis_r')
    ax.scatter(D_vals, H_vals, c='white', edgecolor='k', s=40, zorder=5, linewidth=0.5)
    cb = fig.colorbar(cs, ax=ax, label='LCOH (USD/MWh)')
    ax.set_xlabel('Tank Diameter (m)')
    ax.set_ylabel('Tank Height (m)')
    ax.set_title('LCOH vs Tank Geometry (PI, A=1000 m$^2$)')
    fig.tight_layout()
    _save(fig, 'fig12_lcoh_contour')


# ── Fig 13: Sensitivity tornado ──────────────────────────────────────
def fig13_sensitivity(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('13', 'no metrics data')
        return

    # Find baseline (D=7.0, H=5.0, A=1000, dp=0.05, vf=0.40, ins=1.0)
    base_mask = (
        df['tank_diameter_m'].between(6.9, 7.1) &
        df['tank_height_m'].between(4.9, 5.1) &
        df['aperture_m2'].between(990, 1010) &
        df['particle_diameter_m'].between(0.048, 0.052) &
        df['void_fraction'].between(0.39, 0.41) &
        df['insulation_thickness_m'].between(0.98, 1.02)
    )
    baseline = df[base_mask]
    if baseline.empty:
        _skip('13', 'no baseline point for sensitivity reference')
        return

    baseline_sf = baseline['sf_thermal_pct'].mean()

    # Find variations: only one parameter changed at a time
    variations = []
    for _, row in df.iterrows():
        if row['tank_diameter_m'] != 7.0 or row['tank_height_m'] != 5.0 or row['aperture_m2'] != 1000.0:
            continue
        changes = []
        if abs(row['particle_diameter_m'] - 0.05) > 0.001:
            changes.append(('dp', row['particle_diameter_m'], 0.05))
        if abs(row['void_fraction'] - 0.40) > 0.005:
            changes.append(('void frac.', row['void_fraction'], 0.40))
        if abs(row['insulation_thickness_m'] - 1.0) > 0.01:
            changes.append(('insulation', row['insulation_thickness_m'], 1.0))

        for label, val, base_val in changes:
            pct_change = (val - base_val) / base_val * 100
            sf_delta = row['sf_thermal_pct'] - baseline_sf
            variations.append({
                'parameter': f'{label}\n({val:.3f})',
                'pct_change': pct_change,
                'sf_delta': sf_delta,
            })

    if not variations:
        _skip('13', 'no sensitivity variations found')
        return

    var_df = pd.DataFrame(variations)
    var_df = var_df.sort_values('sf_delta')

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['crimson' if v < 0 else 'steelblue' for v in var_df['sf_delta']]
    ax.barh(var_df['parameter'], var_df['sf_delta'], color=colors, edgecolor='k', linewidth=0.5)
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_xlabel(r'$\Delta$ Solar Fraction (%)')
    ax.set_title('Sensitivity of SF to Physical Parameters')
    fig.tight_layout()
    _save(fig, 'fig13_sensitivity')


# ── Fig 14: HTF comparison ───────────────────────────────────────────
def fig14_htf_comparison(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('14', 'no metrics data')
        return

    htf_groups = df.groupby('htf')
    if len(htf_groups) < 2:
        _skip('14', 'only one HTF in data (need comparison)')
        return

    # Filter to baseline geometry
    base = df[
        df['tank_diameter_m'].between(6.9, 7.1) &
        df['tank_height_m'].between(4.9, 5.1) &
        df['aperture_m2'].between(990, 1010)
    ]
    if len(base) < 2:
        base = df

    htf_data = base.groupby('htf').agg(
        sf=('sf_thermal_pct', 'mean'),
        conv=('convergence_rate_pct', 'mean'),
    ).reset_index()

    htf_clean = htf_data['htf'].str.replace('INCOMP::', '').str.replace('::', ' ')

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(htf_data))
    width = 0.35

    bar1 = ax.bar(x - width/2, htf_data['sf'], width, label='Solar Fraction (%)',
                  color='steelblue', edgecolor='k')
    bar2 = ax.bar(x + width/2, htf_data['conv'], width, label='Convergence Rate (%)',
                  color='lightcoral', edgecolor='k')

    ax.set_ylabel('Percentage (%)')
    ax.set_title('HTF Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(htf_clean)
    ax.legend(loc='lower right')
    ax.set_ylim(0, 110)
    for b in bar1:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1,
                f'{b.get_height():.1f}', ha='center', fontsize=9)
    fig.tight_layout()
    _save(fig, 'fig14_htf_comparison')


# ── Fig 15: Mode-hours distribution vs tank volume ───────────────────
def fig15_mode_hours(metrics: pd.DataFrame):
    """Stacked bar chart of operating mode hours vs TES volume, by topology."""
    df = metrics.copy()
    if df.empty:
        _skip('15', 'no metrics data')
        return

    # Find mode columns
    mode_cols = sorted([c for c in df.columns if c.startswith('mode_') and c.endswith('_hours')],
                       key=lambda x: int(x.split('_')[1]))
    if not mode_cols:
        _skip('15', 'no mode_hours columns')
        return

    # Filter to A=1000 for fair comparison
    a1000 = df[df['aperture_m2'].between(990, 1010) & (df['days'] >= 30)].copy()
    if a1000.empty:
        a1000 = df[df['days'] >= 30].copy()

    # Drop rows missing mode data
    for mc in mode_cols:
        if mc in a1000.columns:
            a1000[mc] = a1000[mc].fillna(0)

    for topology in ['Parallel', 'Series']:
        sub = a1000[a1000['topology'].str.lower() == topology.lower()].sort_values('tes_volume_m3')
        if sub.empty:
            continue

        fig, ax = plt.subplots(figsize=(10, 5))
        labels = [f"D={r['tank_diameter_m']:.0f}\nH={r['tank_height_m']:.0f}"
                  for _, r in sub.iterrows()]
        x = np.arange(len(sub))
        width = 0.6
        bottoms = np.zeros(len(sub))

        mode_colors = {'1': '#1f77b4', '2': '#ff7f0e', '3': '#2ca02c',
                       '4': '#d62728', '5': '#9467bd', '6': '#8c564b'}

        for mc in mode_cols:
            mode_num = mc.split('_')[1]
            vals = sub[mc].fillna(0).values
            color = mode_colors.get(mode_num, '#999999')
            ax.bar(x, vals, width, bottom=bottoms, label=f'Mode {mode_num}',
                   color=color, edgecolor='k', linewidth=0.3)
            bottoms += vals

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel('Hours per year')
        ax.set_title(f'{topology} — Mode Distribution vs Tank Geometry (A=1000 m$^2$)')
        ax.legend(loc='upper left', ncol=3, framealpha=0.8, fontsize=9)
        ax.set_ylim(0, 9000)
        fig.tight_layout()
        _save(fig, f'fig15_mode_hours_{topology.lower()}')

    if len(a1000['topology'].unique()) >= 2 and a1000['topology'].nunique() >= 2:
        # Combined comparison: SF vs mode distribution
        fig, ax = plt.subplots(figsize=(7, 5))
        for topo in ['Parallel', 'Series']:
            topo_data = a1000[a1000['topology'].str.lower() == topo.lower()]
            if topo_data.empty:
                continue
            for mc in mode_cols:
                mode_num = mc.split('_')[1]
                avg_h = topo_data[mc].mean()
                ax.bar(f'{topo} M{mode_num}', avg_h, color=mode_colors.get(mode_num, '#999'),
                       edgecolor='k', linewidth=0.3)
        ax.set_ylabel('Mean annual hours')
        ax.set_title('PI vs SD — Mode Utilization (A=1000 m$^2$)')
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
        _save(fig, 'fig15_mode_hours_comparison')


# ── Fig 16: Corrected round-trip efficiency vs SM ────────────────────
def fig16_roundtrip_vs_sm(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('16', 'no metrics data')
        return

    # Prefer corrected RTE, fall back to raw
    rte_col = 'rte_corrected_pct' if 'rte_corrected_pct' in df.columns else 'round_trip_eff_pct'
    rt_ok = df.dropna(subset=[rte_col, 'solar_multiple'])
    if rt_ok.empty:
        _skip('16', 'no round-trip efficiency data')
        return

    geo = rt_ok[
        (rt_ok['tank_diameter_m'].between(6.9, 7.1)) &
        (rt_ok['tank_height_m'].between(4.9, 5.1))
    ]
    if len(geo) < 2:
        geo = rt_ok

    fig, ax = plt.subplots(figsize=(7, 5))
    for topo in geo['topology'].unique():
        sub = geo[geo['topology'] == topo].sort_values('solar_multiple')
        ax.plot(sub['solar_multiple'], sub[rte_col],
                'D-', label=topo, markersize=8, linewidth=2)

    ax.set_xlabel('Solar Multiple (SM)')
    ax.set_ylabel('Storage Utilization Efficiency (%)')
    ax.set_title('TES Storage Utilization vs Solar Multiple')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    _save(fig, 'fig16_roundtrip_vs_sm')


# ── Fig 17: LCOH vs SF Pareto front ──────────────────────────────────
def fig17_lcoh_vs_sf_pareto(metrics: pd.DataFrame):
    df = metrics.copy()
    if df.empty:
        _skip('17', 'no metrics data')
        return

    pareto_ok = df.dropna(subset=['sf_thermal_pct', 'lcoh_usd_per_MWh'])
    if pareto_ok.empty:
        _skip('17', 'no SF+LCOH data')
        return

    # Color by topology or tank volume
    color_col = 'tes_volume_m3' if 'tes_volume_m3' in pareto_ok.columns else 'solar_multiple'

    fig, ax = plt.subplots(figsize=(8, 6))

    for topo in pareto_ok['topology'].unique():
        sub = pareto_ok[pareto_ok['topology'] == topo]
        sc = ax.scatter(sub['sf_thermal_pct'], sub['lcoh_usd_per_MWh'],
                        c=sub[color_col], cmap='coolwarm', s=80,
                        edgecolor='k', alpha=0.85, label=topo, marker='o' if topo == 'Parallel' else 's')

    # Draw Pareto front (lower-left envelope)
    sf_lcoh = pareto_ok[['sf_thermal_pct', 'lcoh_usd_per_MWh']].values
    # Sort by SF descending, compute running min LCOH
    sorted_idx = np.argsort(-sf_lcoh[:, 0])
    sf_sorted = sf_lcoh[sorted_idx, 0]
    lcoh_sorted = sf_lcoh[sorted_idx, 1]
    pareto_lcoh = np.minimum.accumulate(lcoh_sorted)
    # Only keep points that strictly improve LCOH
    pareto_mask = np.diff(pareto_lcoh, prepend=np.inf) < 0
    ax.plot(sf_sorted[pareto_mask], pareto_lcoh[pareto_mask],
            'k--', linewidth=1.5, alpha=0.6, label='Pareto front')

    fig.colorbar(sc, ax=ax, label=f'{color_col.replace("_", " ").title()}')
    ax.set_xlabel('Solar Fraction (%)')
    ax.set_ylabel('LCOH (USD/MWh)')
    ax.set_title('LCOH vs Solar Fraction — Pareto Frontier')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save(fig, 'fig17_lcoh_vs_sf_pareto')


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

FIG_FUNCTIONS = {
    '02': (fig02_weather, []),
    '03': (fig03_tes_colormap, []),
    '04': (fig04_summer_week, []),
    '05': (fig05_winter_week, []),
    '06': (fig06_monthly_energy, []),
    '07': (fig07_zinc_pool, []),
    '08': (fig08_topology_sf, ['metrics']),
    '09': (fig09_sf_vs_aperture, ['metrics']),
    '10': (fig10_lcoh_vs_aperture, ['metrics']),
    '11': (fig11_sf_contour, ['metrics']),
    '12': (fig12_lcoh_contour, ['metrics']),
    '13': (fig13_sensitivity, ['metrics']),
    '14': (fig14_htf_comparison, ['metrics']),
    '15': (fig15_mode_hours, ['metrics']),
    '16': (fig16_roundtrip_vs_sm, ['metrics']),
    '17': (fig17_lcoh_vs_sf_pareto, ['metrics']),
}


def main():
    parser = argparse.ArgumentParser(description='Generate publication figures.')
    parser.add_argument('--figures', type=str, default=None,
                        help='Comma-separated figure numbers to generate (e.g. "8,9,10"). Default: all.')
    parser.add_argument('--metrics', type=str, default=None,
                        help='Path to parametric_metrics.csv (default: results/parametric_metrics.csv).')
    args = parser.parse_args()

    # Determine which figures to generate
    if args.figures:
        wanted = set(args.figures.split(','))
    else:
        wanted = set(FIG_FUNCTIONS.keys())

    # Load metrics (once, shared by metric-dependent figures)
    metrics = pd.DataFrame()
    metrics_loaded = False

    for fig_num in sorted(wanted, key=int):
        if fig_num not in FIG_FUNCTIONS:
            print(f"  Unknown figure: {fig_num}")
            continue

        func, deps = FIG_FUNCTIONS[fig_num]
        print(f"  Fig {fig_num} ...", end=' ', flush=True)

        if 'metrics' in deps and not metrics_loaded:
            metrics = load_metrics(args.metrics)
            metrics_loaded = True

        try:
            if 'metrics' in deps:
                func(metrics)
            else:
                func()
            # Verify: check if output files exist
            svg_files = [f for f in os.listdir(FIG_DIR) if f.startswith(f'fig{fig_num}_') and f.endswith('.svg')]
            if svg_files:
                GENERATED_FIGS.add(fig_num)
                print("OK")
            else:
                print("SKIPPED" if fig_num in SKIPPED else "OK (no output?)")
        except Exception as e:
            print(f"FAILED: {e}"); import traceback; traceback.print_exc()
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f" Generated: {len(GENERATED_FIGS)} figures -> {FIG_DIR}")
    if SKIPPED:
        print(f" Skipped:   {len(SKIPPED)} figures")
        for fig_num, reason in sorted(SKIPPED.items()):
            print(f"   - fig{fig_num}: {reason}")
    print(f"{'='*60}")


if __name__ == '__main__':
    import json  # needed for tes_profile parsing
    main()
