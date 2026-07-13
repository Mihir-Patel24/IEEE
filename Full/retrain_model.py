"""
retrain_model.py
Retrains GradientBoosting VB + RUL models from master_features.csv
and saves a new best_model.pkl compatible with the current scikit-learn.

Run:
    python retrain_model.py
"""

import os, warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "tool-wear-ai", "data", "processed", "master_features.csv")
OUT_PATH  = os.path.join(BASE, "tool-wear-ai", "backend", "model", "best_model.pkl")

WEAR_LIMIT = 0.3   # mm — ISO 8688

SENSOR_COLS = ["smcAC", "smcDC", "vib_table", "vib_spindle", "AE_table", "AE_spindle"]
STATS       = ["mean", "std", "rms", "max", "min", "var", "skew", "kurtosis"]

FEATURE_COLS = (
    [f"{s}__{st}" for s in SENSOR_COLS for st in STATS]
    + ["time", "DOC", "feed", "material_enc", "run_norm", "VB_lag1", "VB_lag2", "VB_diff"]
)

print("=" * 60)
print("  RETRAIN — scikit-learn", end=" ")
import sklearn; print(sklearn.__version__)
print("=" * 60)

# ── Load data ─────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"  Loaded  : {df.shape[0]} rows × {df.shape[1]} cols")

# Drop rows where VB is null
df = df.dropna(subset=["VB"]).reset_index(drop=True)
print(f"  After dropna(VB): {len(df)} rows")

# Ensure material_enc exists
if "material_enc" not in df.columns:
    df["material_enc"] = (df["material"] - 1).astype(int)

# Ensure RUL_time exists
if "RUL_time" not in df.columns:
    for c, grp in df.groupby("case"):
        max_t = grp["time"].max()
        df.loc[df["case"] == c, "RUL_time"] = max_t - df.loc[df["case"] == c, "time"]

# ── Train / test split (case-wise, no leakage) ────────────────────
all_cases  = sorted(df["case"].unique())
np.random.seed(42)
test_cases  = list(np.random.choice(all_cases, size=max(1, len(all_cases) // 4), replace=False))
train_cases = [c for c in all_cases if c not in test_cases]

train_df = df[df["case"].isin(train_cases)].reset_index(drop=True)
test_df  = df[df["case"].isin(test_cases)].reset_index(drop=True)
print(f"  Train cases: {train_cases}  ({len(train_df)} rows)")
print(f"  Test  cases: {test_cases}  ({len(test_df)} rows)")

# ── Preprocessing ─────────────────────────────────────────────────
# Only keep feature cols that actually exist in the CSV
available = [c for c in FEATURE_COLS if c in df.columns]
missing   = [c for c in FEATURE_COLS if c not in df.columns]
if missing:
    print(f"  [WARN] Missing feature cols (will be zero-filled): {missing}")

def prep(frame, cols):
    X = pd.DataFrame(index=frame.index)
    for c in cols:
        X[c] = frame[c] if c in frame.columns else 0.0
    return X[cols].replace([np.inf, -np.inf], np.nan).values.astype(float)

X_tr_raw = prep(train_df, FEATURE_COLS)
X_te_raw = prep(test_df,  FEATURE_COLS)

imputer = SimpleImputer(strategy="median")
X_tr_raw = imputer.fit_transform(X_tr_raw)
X_te_raw = imputer.transform(X_te_raw)

X_tr_raw = np.nan_to_num(X_tr_raw, nan=0.0, posinf=1e6, neginf=-1e6)
X_te_raw = np.nan_to_num(X_te_raw, nan=0.0, posinf=1e6, neginf=-1e6)

scaler  = RobustScaler()
X_train = scaler.fit_transform(X_tr_raw)
X_test  = scaler.transform(X_te_raw)

X_train = np.nan_to_num(X_train, nan=0.0, posinf=10.0, neginf=-10.0)
X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=10.0, neginf=-10.0)

y_vb_train  = train_df["VB"].fillna(train_df["VB"].median()).values.astype(float)
y_vb_test   = test_df["VB"].fillna(test_df["VB"].median()).values.astype(float)
y_rul_train = train_df["RUL_time"].fillna(0).values.astype(float)
y_rul_test  = test_df["RUL_time"].fillna(0).values.astype(float)

# ── Train GradientBoosting ────────────────────────────────────────
print("\n  Training VB model (GradientBoosting)…")
vb_model = GradientBoostingRegressor(
    n_estimators=400, learning_rate=0.04, max_depth=4,
    subsample=0.8, min_samples_leaf=2, random_state=42
)
vb_model.fit(X_train, y_vb_train)
vb_pred = vb_model.predict(X_test)
vb_mae  = mean_absolute_error(y_vb_test, vb_pred)
vb_rmse = np.sqrt(mean_squared_error(y_vb_test, vb_pred))
vb_r2   = r2_score(y_vb_test, vb_pred)
print(f"  VB  MAE={vb_mae:.4f} mm  RMSE={vb_rmse:.4f} mm  R²={vb_r2:.4f}")

print("  Training RUL model (GradientBoosting)…")
rul_model = GradientBoostingRegressor(
    n_estimators=400, learning_rate=0.04, max_depth=4,
    subsample=0.8, min_samples_leaf=2, random_state=42
)
rul_model.fit(X_train, y_rul_train)
rul_pred = rul_model.predict(X_test)
rul_mae  = mean_absolute_error(y_rul_test, rul_pred)
rul_r2   = r2_score(y_rul_test, rul_pred)
print(f"  RUL MAE={rul_mae:.4f} min  R²={rul_r2:.4f}")

# ── Save bundle ───────────────────────────────────────────────────
bundle = {
    "model_name"  : "Gradient Boosting",
    "vb_model"    : vb_model,
    "rul_model"   : rul_model,
    "imputer"     : imputer,
    "scaler"      : scaler,
    "feature_cols": FEATURE_COLS,
    "wear_limit"  : WEAR_LIMIT,
    "vb_metrics"  : {"MAE": vb_mae, "RMSE": vb_rmse, "R2": vb_r2},
    "rul_metrics" : {"MAE": rul_mae, "RMSE": 0.0,    "R2": rul_r2},
    "sklearn_version": sklearn.__version__,
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
joblib.dump(bundle, OUT_PATH)
print(f"\n  [OK] Saved -> {OUT_PATH}")
print(f"  sklearn {sklearn.__version__} | VB R2={vb_r2:.4f} | RUL R2={rul_r2:.4f}")
print("=" * 60)
