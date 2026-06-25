
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("WEEK 2: DATA PREPROCESSING, EDA & BASELINE MODEL")
print("="*60)

# -------------------------------------------------------
# 1. LOAD DATASETS
# -------------------------------------------------------
mill = pd.read_csv(r'd:\IEEE\mill.csv', index_col=0)
ai4i = pd.read_csv(r'd:\IEEE\ai4i2020.csv')

print("\n--- MILL DATASET ---")
print(f"Shape: {mill.shape}")
print(f"Columns: {mill.columns.tolist()}")
print(f"\nData Types:\n{mill.dtypes}")

print("\n--- AI4I 2020 DATASET ---")
print(f"Shape: {ai4i.shape}")
print(f"Columns: {ai4i.columns.tolist()}")

# -------------------------------------------------------
# 2. MISSING VALUE ANALYSIS
# -------------------------------------------------------
print("\n" + "="*60)
print("2. MISSING VALUE ANALYSIS")
print("="*60)

mill_missing = mill.isnull().sum()
mill_missing_pct = (mill.isnull().sum() / len(mill) * 100).round(2)
mill_mv = pd.DataFrame({'Missing Count': mill_missing, 'Missing %': mill_missing_pct})
print("\nMill Dataset Missing Values:")
print(mill_mv[mill_mv['Missing Count'] > 0])

ai4i_missing = ai4i.isnull().sum()
print(f"\nAI4I Total Missing Values: {ai4i_missing.sum()}")

# -------------------------------------------------------
# 3. DESCRIPTIVE STATISTICS
# -------------------------------------------------------
print("\n" + "="*60)
print("3. DESCRIPTIVE STATISTICS")
print("="*60)
print("\nMill Dataset Statistics:")
print(mill.describe().round(4))
print("\nAI4I Dataset Statistics:")
ai4i_numeric = ai4i.select_dtypes(include=np.number)
print(ai4i_numeric.describe().round(4))

# -------------------------------------------------------
# 4. PREPROCESSING
# -------------------------------------------------------
print("\n" + "="*60)
print("4. DATA PREPROCESSING")
print("="*60)

# Mill - Handle missing VB via interpolation within each case
mill_clean = mill.copy()
def fill_vb(group):
    group = group.copy()
    group['VB'] = group['VB'].interpolate(method='linear').ffill().bfill()
    return group
mill_clean = mill_clean.groupby('case', group_keys=False).apply(fill_vb)
if mill_clean['VB'].isnull().sum() > 0:
    mill_clean['VB'].fillna(mill_clean['VB'].median(), inplace=True)

print(f"Mill VB missing before: {mill['VB'].isnull().sum()}")
print(f"Mill VB missing after:  {mill_clean['VB'].isnull().sum()}")

# Encode material
mill_clean['material_encoded'] = mill_clean['material'].astype(int)

# AI4I preprocessing
ai4i_clean = ai4i.copy()
ai4i_clean.drop(columns=['UDI', 'Product ID'], inplace=True, errors='ignore')
type_map = {'L': 0, 'M': 1, 'H': 2}
if 'Type' in ai4i_clean.columns:
    ai4i_clean['Type_encoded'] = ai4i_clean['Type'].map(type_map)
    ai4i_clean.drop(columns=['Type'], inplace=True)

print(f"\nMill after preprocessing: {mill_clean.shape}")
print(f"AI4I after preprocessing: {ai4i_clean.shape}")

# -------------------------------------------------------
# 5. FEATURE ENGINEERING
# -------------------------------------------------------
print("\n" + "="*60)
print("5. FEATURE ENGINEERING")
print("="*60)

sensor_cols = ['smcAC', 'smcDC', 'vib_table', 'vib_spindle', 'AE_table', 'AE_spindle']

# Per-run aggregation of sensor signals
agg_dict = {}
for col in sensor_cols:
    for stat in ['mean', 'std', 'max', 'min']:
        agg_dict[f'{col}_{stat}'] = (col, stat)

mill_feat = mill_clean.groupby(['case', 'run']).agg(**agg_dict).reset_index()

# Add machining parameters and target
param_agg = mill_clean.groupby(['case', 'run']).agg(
    VB=('VB', 'last'),
    time=('time', 'last'),
    DOC=('DOC', 'last'),
    feed=('feed', 'last'),
    material=('material_encoded', 'last')
).reset_index()

mill_feat = mill_feat.merge(param_agg, on=['case', 'run'])
mill_feat = mill_feat.dropna(subset=['VB']).reset_index(drop=True)

# Engineered ratio features
mill_feat['vib_ratio'] = mill_feat['vib_table_mean'] / (mill_feat['vib_spindle_mean'].abs() + 1e-9)
mill_feat['AE_ratio'] = mill_feat['AE_table_mean'] / (mill_feat['AE_spindle_mean'].abs() + 1e-9)
mill_feat['energy_smcAC'] = mill_feat['smcAC_mean'] ** 2 + mill_feat['smcAC_std'] ** 2
mill_feat['energy_vib'] = mill_feat['vib_table_mean'] ** 2 + mill_feat['vib_spindle_mean'] ** 2

print(f"Feature set shape: {mill_feat.shape}")
print(f"All features: {mill_feat.columns.tolist()}")

# -------------------------------------------------------
# 6. CORRELATION ANALYSIS
# -------------------------------------------------------
print("\n" + "="*60)
print("6. CORRELATION ANALYSIS")
print("="*60)

feature_names = [c for c in mill_feat.columns if c not in ['case', 'run', 'VB']]
print(f"Number of model features: {len(feature_names)}")
corr_with_vb = mill_feat[feature_names + ['VB']].corr()['VB'].drop('VB').sort_values(key=abs, ascending=False)
print("\nTop 10 features correlated with VB (Tool Wear):")
print(corr_with_vb.head(10).round(4))

# -------------------------------------------------------
# 7. EDA PLOTS - MILL DATASET
# -------------------------------------------------------
print("\n" + "="*60)
print("7. GENERATING EDA PLOTS")
print("="*60)

fig, axes = plt.subplots(2, 3, figsize=(17, 10))
fig.suptitle('NASA Milling Dataset — Exploratory Data Analysis', fontsize=16, fontweight='bold')

mill_valid = mill_clean.dropna(subset=['VB'])

# (1) VB distribution
axes[0,0].hist(mill_valid['VB'], bins=25, color='#4A90D9', edgecolor='white', linewidth=0.5)
axes[0,0].axvline(0.3, color='red', linestyle='--', linewidth=1.5, label='Wear limit (0.3mm)')
axes[0,0].set_title('Distribution of Tool Wear (VB)', fontweight='bold')
axes[0,0].set_xlabel('VB (mm)')
axes[0,0].set_ylabel('Frequency')
axes[0,0].legend()

# (2) VB over time per case
colors_cases = ['#E74C3C','#3498DB','#2ECC71','#F39C12','#9B59B6','#1ABC9C','#E67E22','#34495E']
for i, case in enumerate(mill_valid['case'].unique()[:8]):
    df_case = mill_valid[mill_valid['case'] == case].sort_values('time')
    axes[0,1].plot(df_case['time'], df_case['VB'], marker='o', markersize=3,
                   label=f'Case {case}', color=colors_cases[i % len(colors_cases)], alpha=0.85)
axes[0,1].set_title('Tool Wear Progression Over Time', fontweight='bold')
axes[0,1].set_xlabel('Time (min)')
axes[0,1].set_ylabel('VB (mm)')
axes[0,1].legend(fontsize=7, ncol=2)

# (3) Sensor correlation heatmap
corr_data = mill_valid[sensor_cols + ['VB']].corr()
sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            ax=axes[0,2], linewidths=0.5, annot_kws={'size': 8})
axes[0,2].set_title('Sensor ↔ Tool Wear Correlation', fontweight='bold')

# (4) VB by Depth of Cut
doc_vals = sorted(mill_valid['DOC'].unique())
for j, doc in enumerate(doc_vals):
    subset = mill_valid[mill_valid['DOC'] == doc]
    axes[1,0].scatter(subset['time'], subset['VB'], alpha=0.55, s=18,
                      label=f'DOC={doc}', color=colors_cases[j % len(colors_cases)])
axes[1,0].set_title('Tool Wear vs Time (by Depth of Cut)', fontweight='bold')
axes[1,0].set_xlabel('Time (min)')
axes[1,0].set_ylabel('VB (mm)')
axes[1,0].legend(fontsize=9)

# (5) Average VB by material
mat_labels = {1: 'Cast Iron', 2: 'Steel'}
mill_valid = mill_valid.copy()
mill_valid['material_name'] = mill_valid['material'].map(mat_labels)
mat_vb = mill_valid.groupby('material_name')['VB'].mean()
bar_colors = ['#3498DB','#E74C3C'][:len(mat_vb)]
bars = axes[1,1].bar(mat_vb.index, mat_vb.values, color=bar_colors, edgecolor='white', linewidth=0.5)
for bar, val in zip(bars, mat_vb.values):
    axes[1,1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003, f'{val:.3f} mm', ha='center', fontsize=10)
axes[1,1].set_title('Average Tool Wear by Material', fontweight='bold')
axes[1,1].set_xlabel('Material')
axes[1,1].set_ylabel('Mean VB (mm)')

# (6) Feed rate vs VB
feed_vals = sorted(mill_valid['feed'].unique())
for j, feed in enumerate(feed_vals):
    subset = mill_valid[mill_valid['feed'] == feed]
    axes[1,2].scatter(subset['time'], subset['VB'], alpha=0.5, s=18,
                      label=f'Feed={feed}', color=colors_cases[j % len(colors_cases)])
axes[1,2].set_title('Tool Wear vs Time (by Feed Rate)', fontweight='bold')
axes[1,2].set_xlabel('Time (min)')
axes[1,2].set_ylabel('VB (mm)')
axes[1,2].legend(fontsize=9)

plt.tight_layout()
plt.savefig(r'd:\IEEE\eda_mill.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: eda_mill.png")

# -------------------------------------------------------
# EDA - AI4I DATASET
# -------------------------------------------------------
fig2, axes2 = plt.subplots(2, 3, figsize=(17, 10))
fig2.suptitle('AI4I 2020 Dataset — Exploratory Data Analysis', fontsize=16, fontweight='bold')

# (1) Machine Failure Pie
fc_col = [c for c in ai4i.columns if 'machine failure' in c.lower()][0]
fc_counts = ai4i[fc_col].value_counts().sort_index()
labels = ['No Failure', 'Failure'] if len(fc_counts) == 2 else [str(x) for x in fc_counts.index]
axes2[0,0].pie(fc_counts.values, labels=labels, autopct='%1.1f%%',
               colors=['#2ECC71', '#E74C3C'], startangle=90, textprops={'fontsize': 11})
axes2[0,0].set_title('Machine Failure Distribution', fontweight='bold')

# (2) Tool Wear Distribution
tw_col = [c for c in ai4i.columns if 'tool wear' in c.lower()][0]
axes2[0,1].hist(ai4i[tw_col], bins=30, color='#9B59B6', edgecolor='white')
axes2[0,1].set_title('Distribution of Tool Wear (AI4I)', fontweight='bold')
axes2[0,1].set_xlabel(tw_col)
axes2[0,1].set_ylabel('Frequency')

# (3) Rotational Speed Distribution
rpm_col = [c for c in ai4i.columns if 'rotational' in c.lower()][0]
axes2[0,2].hist(ai4i[rpm_col], bins=30, color='#F39C12', edgecolor='white')
axes2[0,2].set_title('Rotational Speed Distribution', fontweight='bold')
axes2[0,2].set_xlabel(rpm_col)
axes2[0,2].set_ylabel('Frequency')

# (4) Torque Distribution
torque_col = [c for c in ai4i.columns if 'torque' in c.lower()][0]
axes2[1,0].hist(ai4i[torque_col], bins=30, color='#E74C3C', edgecolor='white')
axes2[1,0].set_title('Torque Distribution', fontweight='bold')
axes2[1,0].set_xlabel(torque_col)
axes2[1,0].set_ylabel('Frequency')

# (5) Failure Type Frequency
ft_tags = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
ft_cols = [c for c in ai4i.columns if any(ft == c.strip() for ft in ft_tags)]
if not ft_cols:
    ft_cols = [c for c in ai4i.columns if any(ft in c for ft in ft_tags)]
ft_counts = {c: int(ai4i[c].sum()) for c in ft_cols}
bars_ft = axes2[1,1].bar(ft_counts.keys(), ft_counts.values(),
                          color=['#3498DB','#E74C3C','#2ECC71','#F39C12','#9B59B6'][:len(ft_counts)], edgecolor='white')
for bar, val in zip(bars_ft, ft_counts.values()):
    axes2[1,1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, str(val), ha='center', fontsize=9)
axes2[1,1].set_title('Failure Type Frequency', fontweight='bold')
axes2[1,1].set_ylabel('Count')
axes2[1,1].set_xlabel('Failure Type')

# (6) Correlation Heatmap
num_ai4i = ai4i.select_dtypes(include=np.number).drop(columns=['UDI'], errors='ignore')
corr_ai4i = num_ai4i.corr()
sns.heatmap(corr_ai4i, cmap='coolwarm', ax=axes2[1,2], annot=False, linewidths=0.3)
axes2[1,2].set_title('Feature Correlation Heatmap (AI4I)', fontweight='bold')

plt.tight_layout()
plt.savefig(r'd:\IEEE\eda_ai4i.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: eda_ai4i.png")

# -------------------------------------------------------
# 8. BASELINE MODEL — TOOL WEAR REGRESSION
# -------------------------------------------------------
print("\n" + "="*60)
print("8. BASELINE MODEL TRAINING")
print("="*60)

X = mill_feat[feature_names].values.astype(float)
y = mill_feat['VB'].values.astype(float)
print(f"Feature matrix shape: {X.shape}")

# Impute
imputer = SimpleImputer(strategy='median')
X = imputer.fit_transform(X)

# Scale
scaler = StandardScaler()
X = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

model_dict = {
    'Linear Regression': LinearRegression(),
    'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
}

results = {}
for name, mdl in model_dict.items():
    mdl.fit(X_train, y_train)
    y_pred = mdl.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)
    results[name] = {'MAE': round(mae, 4), 'RMSE': round(rmse, 4), 'R2': round(r2, 4)}
    print(f"\n{name}:")
    print(f"  MAE : {mae:.4f} mm")
    print(f"  RMSE: {rmse:.4f} mm")
    print(f"  R²  : {r2:.4f}")

# Feature importance from RF
rf_mdl = model_dict['Random Forest']
n_features_used = X_train.shape[1]  # should match feature_names
feat_imp = pd.Series(rf_mdl.feature_importances_, index=feature_names[:n_features_used]).sort_values(ascending=False)
print(f"\nTop 10 Feature Importances (Random Forest):")
print(feat_imp.head(10).round(4))

# -------------------------------------------------------
# 9. RESULTS VISUALIZATION
# -------------------------------------------------------
fig3, axes3 = plt.subplots(1, 3, figsize=(18, 5))
fig3.suptitle('Baseline Model Results — Tool Wear Prediction (Mill Dataset)', fontsize=14, fontweight='bold')
bar_colors = ['#3498DB', '#E74C3C', '#2ECC71']

# MAE comparison
mae_vals = [results[m]['MAE'] for m in results]
b1 = axes3[0].bar(results.keys(), mae_vals, color=bar_colors, edgecolor='white')
axes3[0].set_title('Mean Absolute Error (MAE)', fontweight='bold')
axes3[0].set_ylabel('MAE (mm)')
for bar, val in zip(b1, mae_vals):
    axes3[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001, f'{val:.4f}', ha='center', fontsize=9)
axes3[0].set_xticklabels(list(results.keys()), rotation=15, ha='right')

# R² comparison
r2_vals = [results[m]['R2'] for m in results]
b2 = axes3[1].bar(results.keys(), r2_vals, color=bar_colors, edgecolor='white')
axes3[1].set_title('R² Score', fontweight='bold')
axes3[1].set_ylabel('R²')
axes3[1].set_ylim(0, 1.05)
for bar, val in zip(b2, r2_vals):
    axes3[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, f'{val:.4f}', ha='center', fontsize=9)
axes3[1].set_xticklabels(list(results.keys()), rotation=15, ha='right')

# Feature importance
top10 = feat_imp.head(10)
axes3[2].barh(top10.index[::-1], top10.values[::-1], color='#9B59B6')
axes3[2].set_title('Top 10 Feature Importances (RF)', fontweight='bold')
axes3[2].set_xlabel('Importance Score')

plt.tight_layout()
plt.savefig(r'd:\IEEE\baseline_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved: baseline_results.png")

# Actual vs Predicted (best model)
best_name = max(results, key=lambda m: results[m]['R2'])
y_pred_best = model_dict[best_name].predict(X_test)

fig4, ax4 = plt.subplots(figsize=(7, 6))
ax4.scatter(y_test, y_pred_best, alpha=0.6, color='#3498DB', s=45, label='Predictions', edgecolors='white', linewidth=0.5)
lims = [min(y_test.min(), y_pred_best.min()) - 0.02, max(y_test.max(), y_pred_best.max()) + 0.02]
ax4.plot(lims, lims, 'r--', linewidth=2, label='Perfect prediction')
ax4.set_xlabel('Actual VB (mm)', fontsize=12)
ax4.set_ylabel('Predicted VB (mm)', fontsize=12)
ax4.set_title(f'Actual vs Predicted Tool Wear\n({best_name})', fontsize=13, fontweight='bold')
ax4.legend()
ax4.text(0.05, 0.90, f'R² = {results[best_name]["R2"]:.4f}\nMAE = {results[best_name]["MAE"]:.4f} mm',
         transform=ax4.transAxes, fontsize=11, bbox=dict(boxstyle='round', facecolor='#FFF9C4', alpha=0.8))
plt.tight_layout()
plt.savefig(r'd:\IEEE\actual_vs_predicted.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: actual_vs_predicted.png")

# -------------------------------------------------------
# 10. SUMMARY
# -------------------------------------------------------
print("\n" + "="*60)
print("WEEK 2 SUMMARY")
print("="*60)
print(f"\nMill Dataset:")
print(f"  Records       : {len(mill)}")
print(f"  Missing VB    : {mill['VB'].isnull().sum()} ({mill['VB'].isnull().sum()/len(mill)*100:.1f}%) → fixed via interpolation")
print(f"  Cases         : {mill['case'].nunique()}")
print(f"  Materials     : Cast Iron (1), Steel (2)")
print(f"  VB range      : {mill['VB'].min():.3f} – {mill['VB'].max():.3f} mm")
print(f"  Mean VB       : {mill['VB'].mean():.3f} mm")
print(f"  Features built: {len(feature_names)}")

print(f"\nAI4I Dataset:")
print(f"  Records       : {len(ai4i)}")
print(f"  Missing values: {ai4i.isnull().sum().sum()}")
fc = [c for c in ai4i.columns if 'machine failure' in c.lower()][0]
print(f"  Failure rate  : {ai4i[fc].mean()*100:.2f}%")
print(f"  No Failure    : {(ai4i[fc]==0).sum()}, Failure: {(ai4i[fc]==1).sum()}")

print(f"\nBaseline Model Results (Mill – Tool Wear Regression):")
for name, res in results.items():
    print(f"  {name:25s}: MAE={res['MAE']:.4f}  RMSE={res['RMSE']:.4f}  R²={res['R2']:.4f}")
print(f"\n  Best model: {best_name}  (R²={results[best_name]['R2']:.4f})")
print("\nAll plots saved. Analysis complete.")
