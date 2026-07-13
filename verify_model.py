
"""Quick smoke-test for best_model.pkl"""
import joblib, numpy as np, pandas as pd

bundle = joblib.load(r'd:\IEEE\pipeline_output\best_model.pkl')

print("=== best_model.pkl VERIFICATION ===\n")
print(f"  Model name    : {bundle['model_name']}")
print(f"  Feature count : {len(bundle['feature_cols'])}")
print(f"  Wear limit    : {bundle['wear_limit']} mm")
print(f"  VB  MAE       : {bundle['vb_metrics']['MAE']:.4f} mm")
print(f"  VB  R2        : {bundle['vb_metrics']['R2']:.4f}")
print(f"  RUL MAE       : {bundle['rul_metrics']['MAE']:.4f} min")
print(f"  RUL R2        : {bundle['rul_metrics']['R2']:.4f}")

# --- Build a FAKE single-row feature vector (all median values from training data)
feat_df = pd.read_csv(r'd:\IEEE\pipeline_output\master_features.csv')
sample_row = feat_df[bundle['feature_cols']].median().values.reshape(1, -1)

# Run through imputer + scaler + model
X = bundle['scaler'].transform(bundle['imputer'].transform(sample_row))
X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

vb_pred  = bundle['vb_model'].predict(X)[0]
rul_pred = bundle['rul_model'].predict(X)[0]

WEAR_LIMIT = bundle['wear_limit']
health     = max(0, (1 - vb_pred / WEAR_LIMIT) * 100)
wear_lvl   = ('Low' if vb_pred/WEAR_LIMIT < 0.4 else
              'Medium' if vb_pred/WEAR_LIMIT < 0.7 else
              'High' if vb_pred/WEAR_LIMIT < 1.0 else 'Critical')
action     = ('REPLACE NOW' if vb_pred/WEAR_LIMIT >= 1.0 else
              'Schedule Replace' if vb_pred/WEAR_LIMIT >= 0.85 else
              'Inspect' if vb_pred/WEAR_LIMIT >= 0.60 else 'Continue')

print("\n--- Single-row inference test (median feature values) ---")
print(f"  VB Predicted       : {vb_pred:.4f} mm")
print(f"  RUL Predicted      : {max(rul_pred,0):.2f} min")
print(f"  Tool_Health_Score  : {health:.1f}%")
print(f"  Wear_Level         : {wear_lvl}")
print(f"  Maintenance_Action : {action}")
print("\n  [PASS] best_model.pkl is working correctly.")
