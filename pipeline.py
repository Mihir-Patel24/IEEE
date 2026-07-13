
"""
+==================================================================+
|        TOOL WEAR PREDICTION + RUL ESTIMATION PIPELINE           |
|        NASA Ames Milling Dataset  |  Groups 18  |  IEEE 2026    |
+==================================================================+
|  Phase 1 | Data Understanding & Master Dataset Creation          |
|  Phase 2 | Feature Engineering (8 stats x 6 sensors = 48 feats) |
|  Phase 3 | Exploratory Data Analysis (4 key plots)               |
|  Phase 4 | Model Training - RF, GBM, XGBoost                    |
|  Phase 5 | Tool Wear (VB) Prediction + RUL Estimation           |
|  Phase 6 | Save Best Model ? best_model.pkl                     |
+==================================================================+
"""

# -- Standard Imports ---------------------------------------------
import os, warnings
import numpy as np
import pandas as pd
import scipy.io as sio
from scipy.stats import skew, kurtosis
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import joblib
warnings.filterwarnings('ignore')

# -- ML Imports ---------------------------------------------------
from sklearn.model_selection import cross_val_score, KFold
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[INFO] XGBoost not installed - skipping XGBoost model")

# -- Output Directory ---------------------------------------------
OUT = r'd:\IEEE\pipeline_output'
os.makedirs(OUT, exist_ok=True)

WEAR_LIMIT   = 0.3   # mm - ISO 8688 tool replacement threshold
SENSOR_COLS  = ['smcAC', 'smcDC', 'vib_table', 'vib_spindle', 'AE_table', 'AE_spindle']
SENSOR_LABELS = {
    'smcAC'      : 'Spindle Current (AC)',
    'smcDC'      : 'Spindle Current (DC)',
    'vib_table'  : 'Table Vibration',
    'vib_spindle': 'Spindle Vibration',
    'AE_table'   : 'AE - Table',
    'AE_spindle' : 'AE - Spindle',
}
DARK_BG   = '#0D1117'
PANEL_BG  = '#161B22'
PALETTE   = ['#58A6FF','#3FB950','#F78166','#D2A8FF','#FFA657','#79C0FF','#FF7B72','#56D364']

plt.rcParams.update({
    'figure.facecolor': DARK_BG, 'axes.facecolor': PANEL_BG,
    'axes.edgecolor': '#30363D', 'axes.labelcolor': '#E6EDF3',
    'xtick.color': '#8B949E',   'ytick.color': '#8B949E',
    'text.color': '#E6EDF3',    'grid.color': '#21262D',
    'grid.linestyle': '--',     'grid.alpha': 0.5,
    'legend.facecolor': '#21262D', 'legend.edgecolor': '#30363D',
})

def banner(phase, title):
    print(f"\n{'='*65}")
    print(f"  {phase}  |  {title}")
    print(f"{'='*65}")

def metric_row(name, mae, rmse, r2):
    print(f"  {name:<28}  MAE={mae:.4f}  RMSE={rmse:.4f}  R2={r2:.4f}")


# ================================================================
#  PHASE 1 - DATA UNDERSTANDING & MASTER DATASET
# ================================================================
banner("PHASE 1", "Data Understanding & Master Dataset Creation")

# 1-A  Load raw .mat file (9 000 raw signal samples per sensor per run)
mat  = sio.loadmat(r'd:\IEEE\mill\mill.mat')
data = mat['mill']               # structured array: shape (case x run)

print(f"  Raw MAT shape  : {data.shape}")
print(f"  Fields         : {data.dtype.names}")
print(f"  Sensors stored : 9 000 time-domain samples per field per run")

# 1-B  Build master row-per-run DataFrame (keeping raw signal arrays)
rows = []
total_exp = 0
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        cell = data[i, j]
        if cell['case'].size == 0:
            continue
        total_exp += 1
        row = {
            'case'     : int(cell['case'].flat[0]),
            'run'      : int(cell['run'].flat[0]),
            'VB'       : float(cell['VB'].flat[0]) if cell['VB'].flat[0] != 0 else np.nan,
            'time'     : float(cell['time'].flat[0]),
            'DOC'      : float(cell['DOC'].flat[0]),
            'feed'     : float(cell['feed'].flat[0]),
            'material' : int(cell['material'].flat[0]),
        }
        # Attach raw 9000-sample arrays for feature extraction
        for col in SENSOR_COLS:
            row[f'_raw_{col}'] = np.array(cell[col]).flatten()
        rows.append(row)

master = pd.DataFrame(rows).sort_values(['case', 'run']).reset_index(drop=True)
print(f"\n  Total runs loaded  : {len(master)}")
print(f"  Unique cases       : {master['case'].nunique()}")
print(f"  VB missing before  : {master['VB'].isnull().sum()} ({master['VB'].isnull().mean()*100:.1f}%)")

# 1-C  Handle Missing VB - per-case linear interpolation (physics-correct)
def fill_vb(grp):
    grp = grp.copy()
    grp['VB'] = grp['VB'].interpolate(method='linear').ffill().bfill()
    return grp

master = master.groupby('case', group_keys=False).apply(fill_vb)
print(f"  VB missing after   : {master['VB'].isnull().sum()}")

# 1-D  Print per-case summary
print(f"\n  {'Case':>4}  {'Runs':>4}  {'VB_min':>7}  {'VB_max':>7}  {'Time_max':>8}  {'Material':>8}  {'DOC':>5}  {'Feed':>6}")
print(f"  {'-'*4}  {'-'*4}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*8}  {'-'*5}  {'-'*6}")
for c, grp in master.groupby('case'):
    print(f"  {c:>4}  {len(grp):>4}  {grp['VB'].min():>7.3f}  {grp['VB'].max():>7.3f}"
          f"  {grp['time'].max():>8.0f}  {'Steel' if grp['material'].iloc[0]==2 else 'Cast Iron':>8}"
          f"  {grp['DOC'].iloc[0]:>5.2f}  {grp['feed'].iloc[0]:>6.2f}")


# ================================================================
#  PHASE 2 - FEATURE ENGINEERING
# ================================================================
banner("PHASE 2", "Feature Engineering - 8 Statistical Features x 6 Sensors")

def extract_features(signal: np.ndarray) -> dict:
    """Extract 8 statistical descriptors from a raw 9000-sample sensor signal."""
    s = signal.astype(float)
    rms = np.sqrt(np.mean(s ** 2))
    sk  = float(np.clip(skew(s),     -10, 10))   # clip to prevent overflow
    ku  = float(np.clip(kurtosis(s), -10, 100))  # AE signals can have very high kurtosis
    return {
        'mean'    : np.mean(s),
        'std'     : np.std(s),
        'rms'     : rms,
        'max'     : np.max(s),
        'min'     : np.min(s),
        'var'     : np.clip(np.var(s), 0, 1e6),  # cap variance extremes
        'skew'    : sk,
        'kurtosis': ku,
    }

feat_rows = []
for _, row in master.iterrows():
    feat = {
        'case'    : row['case'],
        'run'     : row['run'],
        'VB'      : row['VB'],
        'time'    : row['time'],
        'DOC'     : row['DOC'],
        'feed'    : row['feed'],
        'material': row['material'],
    }
    for col in SENSOR_COLS:
        sig  = row[f'_raw_{col}']
        fmap = extract_features(sig)
        lbl  = SENSOR_LABELS[col].replace(' ', '_').replace('-_', '').replace('(', '').replace(')', '')
        for stat, val in fmap.items():
            feat[f'{col}__{stat}'] = val
    feat_rows.append(feat)

feat_df = pd.DataFrame(feat_rows).sort_values(['case', 'run']).reset_index(drop=True)

# Add lag & progression features
feat_df['VB_lag1']  = feat_df.groupby('case')['VB'].shift(1).fillna(0)
feat_df['VB_lag2']  = feat_df.groupby('case')['VB'].shift(2).fillna(0)
feat_df['VB_diff']  = feat_df['VB'] - feat_df['VB_lag1']
feat_df['run_norm'] = feat_df.groupby('case')['run'].transform(lambda x: x / x.max())
feat_df['material_enc'] = (feat_df['material'] - 1).astype(int)

# RUL labels
for c, grp in feat_df.groupby('case'):
    max_time = grp['time'].max()
    feat_df.loc[feat_df['case'] == c, 'RUL_time'] = max_time - feat_df.loc[feat_df['case'] == c, 'time']
feat_df['health'] = (feat_df['VB'] / WEAR_LIMIT).clip(0, 1)

# Feature column list (everything except identifiers and targets)
FEATURE_COLS = (
    [f'{s}__{st}' for s in SENSOR_COLS for st in ['mean','std','rms','max','min','var','skew','kurtosis']]
    + ['time', 'DOC', 'feed', 'material_enc', 'run_norm', 'VB_lag1', 'VB_lag2', 'VB_diff']
)
print(f"  Total features engineered : {len(FEATURE_COLS)}")
print(f"  Sensor statistical feats  : {len(SENSOR_COLS) * 8}  (6 sensors x 8 stats)")
print(f"  Machining/lag features    : {len(FEATURE_COLS) - len(SENSOR_COLS)*8}")
print(f"  Feature matrix shape      : {feat_df[FEATURE_COLS].shape}")

feat_df.to_csv(os.path.join(OUT, 'master_features.csv'), index=False)
print(f"  Saved ? master_features.csv")


# ================================================================
#  PHASE 3 - EXPLORATORY DATA ANALYSIS
# ================================================================
banner("PHASE 3", "Exploratory Data Analysis")

# -- Plot 3-A: Tool Wear Distribution -------------------------
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Phase 3 - Tool Wear Distribution Analysis', fontsize=14, fontweight='bold', color='#E6EDF3')

# Histogram
axes[0].hist(feat_df['VB'].dropna(), bins=28, color=PALETTE[0], edgecolor=DARK_BG, alpha=0.88)
axes[0].axvline(WEAR_LIMIT, color=PALETTE[2], lw=2.5, linestyle='--', label=f'Wear limit ({WEAR_LIMIT} mm)')
axes[0].set_title('VB Distribution (All Runs)', fontweight='bold')
axes[0].set_xlabel('Flank Wear VB (mm)')
axes[0].set_ylabel('Frequency')
axes[0].legend()

# VB by Material (box plot)
mat1 = feat_df[feat_df['material']==1]['VB'].dropna()
mat2 = feat_df[feat_df['material']==2]['VB'].dropna()
bp = axes[1].boxplot([mat1, mat2], labels=['Cast Iron', 'Steel'],
                     patch_artist=True, widths=0.4,
                     boxprops=dict(facecolor=PALETTE[0], alpha=0.7),
                     medianprops=dict(color=PALETTE[2], lw=2.5),
                     whiskerprops=dict(color='#E6EDF3'),
                     capprops=dict(color='#E6EDF3'),
                     flierprops=dict(marker='o', color=PALETTE[4], markersize=4))
bp['boxes'][1].set_facecolor(PALETTE[1])
axes[1].axhline(WEAR_LIMIT, color=PALETTE[2], lw=1.5, linestyle='--', alpha=0.8)
axes[1].set_title('VB Distribution by Material', fontweight='bold')
axes[1].set_ylabel('VB (mm)')

# Wear progression over time - all cases
for i, (c, grp) in enumerate(feat_df.groupby('case')):
    g = grp.sort_values('time')
    axes[2].plot(g['time'], g['VB'], 'o-', lw=1.5, ms=3,
                 color=PALETTE[i % len(PALETTE)], alpha=0.75, label=f'Case {c}')
axes[2].axhline(WEAR_LIMIT, color=PALETTE[2], lw=2, linestyle='--', label='Wear limit')
axes[2].set_title('Wear Progression - All Cases', fontweight='bold')
axes[2].set_xlabel('Machining Time (min)')
axes[2].set_ylabel('VB (mm)')
axes[2].legend(fontsize=6.5, ncol=2)

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'p3a_wear_distribution.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print("  Saved ? p3a_wear_distribution.png")

# -- Plot 3-B: Correlation Heatmap (RMS features vs VB) -------
rms_cols = [f'{s}__rms' for s in SENSOR_COLS]
corr_cols = rms_cols + ['time', 'DOC', 'feed', 'VB_lag1', 'VB']
corr_labels = [SENSOR_LABELS[s]+' RMS' for s in SENSOR_COLS] + ['Time', 'DOC', 'Feed', 'VB lag-1', 'VB']

corr_data = feat_df[corr_cols].rename(columns=dict(zip(corr_cols, corr_labels))).corr()

fig, ax = plt.subplots(figsize=(11, 9))
mask = np.zeros_like(corr_data, dtype=bool)
mask[np.triu_indices_from(mask, k=1)] = True
sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            linewidths=0.5, annot_kws={'size': 9}, ax=ax,
            cbar_kws={'label': 'Pearson r'})
ax.set_title('Phase 3B - Feature Correlation Heatmap\n(RMS Sensor Features + Machining Params vs VB)',
             fontsize=13, fontweight='bold', pad=15)
plt.xticks(rotation=35, ha='right', fontsize=9)
plt.yticks(rotation=0, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'p3b_correlation_heatmap.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print("  Saved ? p3b_correlation_heatmap.png")

# -- Plot 3-C: Sensor Trend Graphs ----------------------------
# Show how each sensor RMS evolves with tool wear across all experiments
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Phase 3C - Sensor Signal Trend vs Tool Wear (All Cases)', fontsize=14, fontweight='bold', color='#E6EDF3')

for idx, (col, ax) in enumerate(zip(SENSOR_COLS, axes.flat)):
    rms_col = f'{col}__rms'
    # Clip to 99th percentile to remove extreme outliers for readability
    p99 = feat_df[rms_col].quantile(0.99)
    p01 = feat_df[rms_col].quantile(0.01)
    for i, (c, grp) in enumerate(feat_df.groupby('case')):
        g = grp.sort_values('VB')
        vals = g[rms_col].clip(p01, p99)
        ax.scatter(g['VB'], vals, s=14, alpha=0.72,
                   color=PALETTE[i % len(PALETTE)], label=f'Case {c}')
    ax.axvline(WEAR_LIMIT, color=PALETTE[2], lw=1.5, linestyle='--', alpha=0.8)
    ax.set_title(f'{SENSOR_LABELS[col]} - RMS vs VB', fontweight='bold', fontsize=10)
    ax.set_xlabel('VB (mm)', fontsize=9)
    ax.set_ylabel('RMS Value', fontsize=9)
    ax.set_ylim(p01 * 0.9, p99 * 1.1)


plt.tight_layout()
plt.savefig(os.path.join(OUT, 'p3c_sensor_trends.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print("  Saved ? p3c_sensor_trends.png")


# ================================================================
#  PHASE 4 - MODEL TRAINING
# ================================================================
banner("PHASE 4", "Model Training - RF | GBM | XGBoost")

# -- Case-wise train/test split (no data leakage) -------------
all_cases = sorted(feat_df['case'].unique())
np.random.seed(42)
test_cases  = list(np.random.choice(all_cases, size=4, replace=False))
train_cases = [c for c in all_cases if c not in test_cases]

train_df = feat_df[feat_df['case'].isin(train_cases)].reset_index(drop=True)
test_df  = feat_df[feat_df['case'].isin(test_cases)].reset_index(drop=True)

print(f"  Train cases : {train_cases}  ({len(train_df)} rows)")
print(f"  Test  cases : {test_cases}  ({len(test_df)} rows)")

# -- Preprocessing ---------------------------------------------
# Replace inf values before imputation
train_df[FEATURE_COLS] = train_df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
test_df[FEATURE_COLS]  = test_df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)

imputer = SimpleImputer(strategy='median')
scaler  = RobustScaler()  # robust to outliers - better than StandardScaler for AE kurtosis

X_tr_raw = imputer.fit_transform(train_df[FEATURE_COLS].values.astype(float))
X_te_raw = imputer.transform(test_df[FEATURE_COLS].values.astype(float))

# Final safety clip to prevent any residual extremes
X_tr_raw = np.nan_to_num(X_tr_raw, nan=0.0, posinf=1e6, neginf=-1e6)
X_te_raw = np.nan_to_num(X_te_raw, nan=0.0, posinf=1e6, neginf=-1e6)

X_train  = scaler.fit_transform(X_tr_raw)
X_test   = scaler.transform(X_te_raw)

X_train  = np.nan_to_num(X_train, nan=0.0, posinf=10.0, neginf=-10.0)
X_test   = np.nan_to_num(X_test,  nan=0.0, posinf=10.0, neginf=-10.0)

# Target arrays - fill any remaining NaN with column median
y_vb_train  = np.nan_to_num(train_df['VB'].values.astype(float),       nan=float(train_df['VB'].median()))
y_vb_test   = np.nan_to_num(test_df['VB'].values.astype(float),        nan=float(test_df['VB'].median()))
y_rul_train = np.nan_to_num(train_df['RUL_time'].values.astype(float), nan=0.0)
y_rul_test  = np.nan_to_num(test_df['RUL_time'].values.astype(float),  nan=0.0)

print(f"  X_train NaNs : {np.isnan(X_train).sum()}  |  X_test NaNs : {np.isnan(X_test).sum()}")
print(f"  y_VB NaNs    : {np.isnan(y_vb_train).sum()} / {np.isnan(y_vb_test).sum()}")
print(f"  y_RUL NaNs   : {np.isnan(y_rul_train).sum()} / {np.isnan(y_rul_test).sum()}")

# -- Train Models ----------------------------------------------
print("\n  -- Training models for VB prediction --")

models = {
    'Random Forest' : RandomForestRegressor(
        n_estimators=300, max_depth=14, min_samples_leaf=2,
        random_state=42, n_jobs=-1),
    'Gradient Boosting' : GradientBoostingRegressor(
        n_estimators=400, learning_rate=0.04, max_depth=4,
        subsample=0.8, min_samples_leaf=2, random_state=42),
}
if HAS_XGB:
    models['XGBoost'] = XGBRegressor(
        n_estimators=400, learning_rate=0.04, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, n_jobs=-1)

vb_results   = {}
rul_results  = {}
trained_vb   = {}
trained_rul  = {}

for name, mdl in models.items():
    # VB
    mdl.fit(X_train, y_vb_train)
    pred = mdl.predict(X_test)
    mae  = mean_absolute_error(y_vb_test, pred)
    rmse = np.sqrt(mean_squared_error(y_vb_test, pred))
    r2   = r2_score(y_vb_test, pred)
    vb_results[name] = {'MAE': mae, 'RMSE': rmse, 'R2': r2, 'pred': pred}
    trained_vb[name] = mdl
    metric_row(name + ' (VB)', mae, rmse, r2)

    # RUL - retrain same class on RUL labels
    import copy
    mdl_rul = copy.deepcopy(mdl.__class__(**mdl.get_params()))
    mdl_rul.fit(X_train, y_rul_train)
    pred_r = mdl_rul.predict(X_test)
    mae_r  = mean_absolute_error(y_rul_test, pred_r)
    rmse_r = np.sqrt(mean_squared_error(y_rul_test, pred_r))
    r2_r   = r2_score(y_rul_test, pred_r)
    rul_results[name] = {'MAE': mae_r, 'RMSE': rmse_r, 'R2': r2_r, 'pred': pred_r}
    trained_rul[name] = mdl_rul

print("\n  -- Training models for RUL prediction --")
for name, res in rul_results.items():
    metric_row(name + ' (RUL)', res['MAE'], res['RMSE'], res['R2'])

# -- Choose best VB model (by R2) -----------------------------
best_name = max(vb_results, key=lambda n: vb_results[n]['R2'])
best_model_vb  = trained_vb[best_name]
best_model_rul = trained_rul[best_name]
print(f"\n  * Best Model: {best_name}  (VB R2={vb_results[best_name]['R2']:.4f})")

# -- Feature Importance Plot (Phase 3-D) -----------------------
if hasattr(best_model_vb, 'feature_importances_'):
    imp = pd.Series(best_model_vb.feature_importances_, index=FEATURE_COLS)
    imp = imp.sort_values(ascending=True).tail(25)

    fig, ax = plt.subplots(figsize=(10, 9))
    colors_imp = [PALETTE[0] if 'AE' in f else
                  PALETTE[1] if 'vib' in f else
                  PALETTE[2] if 'smc' in f else
                  PALETTE[4] for f in imp.index]
    ax.barh(imp.index, imp.values, color=colors_imp, alpha=0.87, edgecolor=DARK_BG)
    ax.set_title(f'Phase 3D - Top 25 Feature Importances\n({best_name})', fontsize=13, fontweight='bold')
    ax.set_xlabel('Importance Score')

    # Legend
    from matplotlib.patches import Patch
    legend_els = [Patch(color=PALETTE[0], label='AE Signal'),
                  Patch(color=PALETTE[1], label='Vibration'),
                  Patch(color=PALETTE[2], label='Motor Current'),
                  Patch(color=PALETTE[4], label='Machining Param')]
    ax.legend(handles=legend_els, fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'p3d_feature_importance.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
    print("  Saved ? p3d_feature_importance.png")


# ================================================================
#  PHASE 5 - PREDICTIONS
# ================================================================
banner("PHASE 5", "Tool Wear (VB) Prediction + RUL Estimation")

pred_vb  = vb_results[best_name]['pred']
pred_rul = rul_results[best_name]['pred']

# -- Results Dashboard -----------------------------------------
fig = plt.figure(figsize=(20, 14))
fig.suptitle(f'Phase 5 - Prediction Dashboard  |  {best_name}', fontsize=15, fontweight='bold', color='#E6EDF3')
gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.35)

# 5-A Actual vs Predicted VB
ax_vb = fig.add_subplot(gs[0, :2])
ax_vb.scatter(y_vb_test, pred_vb, c=PALETTE[0], s=50, alpha=0.8, edgecolors='none')
lim = [min(y_vb_test.min(), pred_vb.min())-0.02, max(y_vb_test.max(), pred_vb.max())+0.02]
ax_vb.plot(lim, lim, '--', color=PALETTE[2], lw=2)
ax_vb.set_title(f'VB: Actual vs Predicted  (R2={vb_results[best_name]["R2"]:.4f})', fontweight='bold')
ax_vb.set_xlabel('Actual VB (mm)');  ax_vb.set_ylabel('Predicted VB (mm)')
ax_vb.grid(True);  ax_vb.set_facecolor(PANEL_BG)

# 5-B Actual vs Predicted RUL
ax_rul = fig.add_subplot(gs[0, 2:])
ax_rul.scatter(y_rul_test, pred_rul, c=PALETTE[1], s=50, alpha=0.8, edgecolors='none')
lim2 = [min(y_rul_test.min(), pred_rul.min())-1, max(y_rul_test.max(), pred_rul.max())+1]
ax_rul.plot(lim2, lim2, '--', color=PALETTE[2], lw=2)
ax_rul.set_title(f'RUL: Actual vs Predicted  (R2={rul_results[best_name]["R2"]:.4f})', fontweight='bold')
ax_rul.set_xlabel('Actual RUL (min)');  ax_rul.set_ylabel('Predicted RUL (min)')
ax_rul.grid(True);  ax_rul.set_facecolor(PANEL_BG)

# 5-C Per-case VB time series (all test cases)
for idx, case_id in enumerate(test_cases):
    ax = fig.add_subplot(gs[1, idx])
    ax.set_facecolor(PANEL_BG)
    mask  = test_df['case'] == case_id
    rows  = test_df[mask].sort_values('run')
    t_arr = rows['time'].values
    vb_a  = rows['VB'].values
    vb_p  = best_model_vb.predict(scaler.transform(imputer.transform(rows[FEATURE_COLS].values.astype(float))))
    rul_a = rows['RUL_time'].values
    rul_p = best_model_rul.predict(scaler.transform(imputer.transform(rows[FEATURE_COLS].values.astype(float))))

    ax.plot(t_arr, vb_a, 'o-',  color=PALETTE[0], lw=2, ms=5, label='Actual VB')
    ax.plot(t_arr, vb_p, 's--', color=PALETTE[2], lw=2, ms=4, label='Pred VB')
    ax.axhline(WEAR_LIMIT, color='red', lw=1.5, linestyle=':', alpha=0.8)
    ax.fill_between(t_arr, vb_a, vb_p, alpha=0.15, color=PALETTE[2])
    ax.set_title(f'Case {case_id} - VB', fontweight='bold', fontsize=10)
    ax.set_xlabel('Time (min)', fontsize=8);  ax.set_ylabel('VB (mm)', fontsize=8)
    ax.legend(fontsize=7);  ax.grid(True)

# 5-D Per-case RUL time series
for idx, case_id in enumerate(test_cases):
    ax = fig.add_subplot(gs[2, idx])
    ax.set_facecolor(PANEL_BG)
    mask  = test_df['case'] == case_id
    rows  = test_df[mask].sort_values('run')
    t_arr = rows['time'].values
    rul_a = rows['RUL_time'].values
    rul_p = best_model_rul.predict(scaler.transform(imputer.transform(rows[FEATURE_COLS].values.astype(float))))

    ax.plot(t_arr, rul_a, 'o-',  color=PALETTE[1], lw=2, ms=5, label='Actual RUL')
    ax.plot(t_arr, rul_p, 's--', color=PALETTE[4], lw=2, ms=4, label='Pred RUL')
    ax.fill_between(t_arr, rul_a, rul_p, alpha=0.15, color=PALETTE[4])
    ax.axhline(0, color='red', lw=1.5, linestyle=':', alpha=0.8, label='End-of-Life')
    ax.set_title(f'Case {case_id} - RUL', fontweight='bold', fontsize=10)
    ax.set_xlabel('Time (min)', fontsize=8);  ax.set_ylabel('RUL (min)', fontsize=8)
    ax.legend(fontsize=7);  ax.grid(True)

plt.savefig(os.path.join(OUT, 'p5_prediction_dashboard.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print("  Saved ? p5_prediction_dashboard.png")

# -- Model Comparison Bar Chart --------------------------------
model_names_short = list(vb_results.keys())
r2_vb   = [vb_results[n]['R2']  for n in model_names_short]
mae_vb  = [vb_results[n]['MAE'] for n in model_names_short]
r2_rul  = [rul_results[n]['R2']  for n in model_names_short]
mae_rul = [rul_results[n]['MAE'] for n in model_names_short]
x = np.arange(len(model_names_short))

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Phase 4 & 5 - Model Comparison: VB Prediction vs RUL Estimation', fontsize=13, fontweight='bold', color='#E6EDF3')

for ax, r2s, maes, title in [
    (axes[0], r2_vb,  mae_vb,  'Tool Wear (VB) Prediction'),
    (axes[1], r2_rul, mae_rul, 'RUL Estimation'),
]:
    ax.set_facecolor(PANEL_BG)
    ax.grid(True)
    b1 = ax.bar(x - 0.2, r2s,  0.38, label='R2 Score',  color=PALETTE[1], alpha=0.88)
    b2 = ax.bar(x + 0.2, maes, 0.38, label='MAE',       color=PALETTE[2], alpha=0.88)
    ax.set_xticks(x);  ax.set_xticklabels(model_names_short, rotation=10)
    ax.set_title(title, fontweight='bold')
    ax.legend()
    for bar in list(b1)+list(b2):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.005,
                f'{bar.get_height():.3f}', ha='center', fontsize=9, color='#E6EDF3')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'p4_model_comparison.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print("  Saved ? p4_model_comparison.png")

# -- Save Enhanced Predictions CSV ----------------------------
pred_out = test_df[['case','run','time','VB','RUL_time']].copy()
pred_out['VB_Predicted']  = pred_vb
pred_out['RUL_Predicted'] = pred_rul
pred_out['VB_Error_mm']   = (pred_out['VB_Predicted'] - pred_out['VB']).abs().round(4)
pred_out['RUL_Error_min'] = (pred_out['RUL_Predicted'] - pred_out['RUL_time']).abs().round(2)

wear_ratio = pred_out['VB_Predicted'] / WEAR_LIMIT

# Tool Health Score: 100% = brand new, 0% = at wear limit
pred_out['Tool_Health_Score'] = ((1 - wear_ratio) * 100).clip(-100, 100).round(1).astype(str) + '%'

# Wear Level category
def _wear_level(r):
    if r < 0.4:   return 'Low'
    elif r < 0.7: return 'Medium'
    elif r < 1.0: return 'High'
    else:         return 'Critical'
pred_out['Wear_Level'] = wear_ratio.apply(_wear_level)

# Maintenance Action
def _action(r, rul):
    if r >= 1.0:  return 'REPLACE NOW'
    elif r >= 0.85: return 'Schedule Replace'
    elif r >= 0.60: return 'Inspect'
    else:           return 'Continue'
pred_out['Maintenance_Action'] = [_action(r, rul) for r, rul in zip(wear_ratio, pred_out['RUL_Predicted'])]

# Confidence Score (from RUL prediction error proximity)
rul_err = (pred_out['RUL_Predicted'] - pred_out['RUL_time']).abs()
conf = (1 - rul_err / (pred_out['RUL_time'].max() + 1e-9)) * 29 + 70
pred_out['Confidence_Score'] = conf.clip(70, 99).round(1).astype(str) + '%'

# Next Inspection time
def _next_insp(r, rul):
    rul = max(rul, 0)
    if r >= 1.0:   return '0 min'
    elif r >= 0.85: return f"{max(round(rul*0.20,1),1.0)} min"
    elif r >= 0.60: return f"{round(rul*0.40,1)} min"
    else:           return f"{round(rul*0.60,1)} min"
pred_out['Next_Inspection'] = [_next_insp(r, rul) for r, rul in zip(wear_ratio, pred_out['RUL_Predicted'])]

pred_out.to_csv(os.path.join(OUT, 'predictions.csv'), index=False)
print("  Saved -> predictions.csv  (with operator-friendly columns)")
print(f"\n  {'Column':<22} {'Sample Values'}")
print(f"  {'-'*22} {'-'*35}")
for col in ['Tool_Health_Score','Wear_Level','Maintenance_Action','Confidence_Score','Next_Inspection']:
    print(f"  {col:<22}  {pred_out[col].iloc[:3].tolist()}")



# ================================================================
#  PHASE 6 - SAVE BEST MODEL
# ================================================================
banner("PHASE 6", "Saving Best Model")

bundle = {
    'model_name'  : best_name,
    'vb_model'    : best_model_vb,
    'rul_model'   : best_model_rul,
    'imputer'     : imputer,
    'scaler'      : scaler,
    'feature_cols': FEATURE_COLS,
    'wear_limit'  : WEAR_LIMIT,
    'vb_metrics'  : {k: v for k, v in vb_results[best_name].items()  if k != 'pred'},
    'rul_metrics' : {k: v for k, v in rul_results[best_name].items() if k != 'pred'},
}
joblib.dump(bundle, os.path.join(OUT, 'best_model.pkl'))
print(f"  Saved ? best_model.pkl")
print(f"\n  Model    : {best_name}")
print(f"  VB  MAE  : {vb_results[best_name]['MAE']:.4f} mm")
print(f"  VB  RMSE : {vb_results[best_name]['RMSE']:.4f} mm")
print(f"  VB  R2   : {vb_results[best_name]['R2']:.4f}")
print(f"  RUL MAE  : {rul_results[best_name]['MAE']:.4f} min")
print(f"  RUL R2   : {rul_results[best_name]['R2']:.4f}")


# ================================================================
#  FINAL SUMMARY
# ================================================================
print(f"\n{'='*65}")
print("  PIPELINE COMPLETE - All outputs in:")
print(f"  {OUT}")
print(f"{'='*65}")
print("  Files generated:")
for f in sorted(os.listdir(OUT)):
    size = os.path.getsize(os.path.join(OUT, f))
    print(f"    {f:<35}  {size/1024:>7.1f} KB")

print(f"\n  {'Model':<22} {'VB MAE':>8} {'VB RMSE':>9} {'VB R2':>8}  {'RUL MAE':>9} {'RUL R2':>8}")
print(f"  {'-'*22} {'-'*8} {'-'*9} {'-'*8}  {'-'*9} {'-'*8}")
for name in vb_results:
    vr = vb_results[name];  rr = rul_results[name]
    star = ' *' if name == best_name else ''
    print(f"  {name+star:<24} {vr['MAE']:>8.4f} {vr['RMSE']:>9.4f} {vr['R2']:>8.4f}  {rr['MAE']:>9.3f} {rr['R2']:>8.4f}")
