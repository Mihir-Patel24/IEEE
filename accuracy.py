
import pandas as pd, numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

df = pd.read_csv(r'd:\IEEE\pipeline_output\predictions.csv').dropna(subset=['VB','VB_Predicted','RUL_time','RUL_Predicted'])
print(f"Rows analysed: {len(df)}")


print("=== TOOL WEAR (VB) ACCURACY ===")
mae  = mean_absolute_error(df['VB'], df['VB_Predicted'])
rmse = np.sqrt(mean_squared_error(df['VB'], df['VB_Predicted']))
r2   = r2_score(df['VB'], df['VB_Predicted'])
mape = (abs(df['VB'] - df['VB_Predicted']) / df['VB'].clip(lower=0.01)).mean() * 100
acc  = (1 - mae / df['VB'].mean()) * 100

print(f"  R2 Score     : {r2:.4f}   --> {r2*100:.2f}% variance explained")
print(f"  MAE          : {mae:.4f} mm")
print(f"  RMSE         : {rmse:.4f} mm")
print(f"  MAPE         : {mape:.2f}%")
print(f"  Accuracy*    : {acc:.2f}%  (1 - MAE/mean_VB)")
print(f"  Within 0.05mm: {(df['VB_Error_mm'] <= 0.05).mean()*100:.1f}% of predictions")
print(f"  Within 0.10mm: {(df['VB_Error_mm'] <= 0.10).mean()*100:.1f}% of predictions")

print()
print("=== RUL ACCURACY ===")
mae_r  = mean_absolute_error(df['RUL_time'], df['RUL_Predicted'])
rmse_r = np.sqrt(mean_squared_error(df['RUL_time'], df['RUL_Predicted']))
r2_r   = r2_score(df['RUL_time'], df['RUL_Predicted'])
rul_err = abs(df['RUL_time'] - df['RUL_Predicted'])
mean_rul = df['RUL_time'].mean()
acc_r  = (1 - mae_r / mean_rul) * 100

print(f"  R2 Score     : {r2_r:.4f}   --> {r2_r*100:.2f}% variance explained")
print(f"  MAE          : {mae_r:.2f} min")
print(f"  RMSE         : {rmse_r:.2f} min")
print(f"  Accuracy*    : {acc_r:.2f}%  (1 - MAE/mean_RUL)")
print(f"  Within 5 min : {(rul_err <= 5).mean()*100:.1f}% of predictions")
print(f"  Within 10 min: {(rul_err <= 10).mean()*100:.1f}% of predictions")

print()
print("=== HEALTH STATUS LABELS ===")
print(df['Health_Status'].value_counts().to_string())

print()
print("=== ALL PREDICTIONS ===")
out = df[['case','run','time','VB','VB_Predicted','VB_Error_mm','RUL_time','RUL_Predicted','Health_Status']].copy()
out['VB_Predicted'] = out['VB_Predicted'].round(4)
out['RUL_Predicted'] = out['RUL_Predicted'].round(1)
print(out.to_string(index=False))
