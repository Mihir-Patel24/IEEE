# Tool Wear AI — Project Structure

```
tool-wear-ai/
├── backend/                        <-- Python backend (give this to back-end dev)
│   ├── main.py                     <-- FastAPI REST API server
│   ├── predict.py                  <-- Importable prediction utility
│   ├── requirements.txt            <-- pip install -r requirements.txt
│   ├── model/
│   │   └── best_model.pkl          <-- Trained Gradient Boosting model (1.4 MB)
│   └── routes/                     <-- Add more route files here if needed
│
├── data/
│   ├── raw/
│   │   └── mill.mat                <-- Original NASA Ames Milling Dataset
│   └── processed/
│       └── master_features.csv     <-- 56-feature engineered dataset (167 rows)
│
├── ml/
│   └── scripts/
│       └── pipeline.py             <-- Full 6-phase training pipeline
│
├── outputs/
│   ├── plots/                      <-- All 6 publication-quality charts
│   │   ├── p3a_wear_distribution.png
│   │   ├── p3b_correlation_heatmap.png
│   │   ├── p3c_sensor_trends.png
│   │   ├── p3d_feature_importance.png
│   │   ├── p4_model_comparison.png
│   │   └── p5_prediction_dashboard.png
│   └── predictions/
│       ├── predictions.csv          <-- Test set predictions (basic)
│       └── predictions_enhanced.csv <-- Test set with all operator columns
│
├── docs/
│   └── API.md                      <-- API documentation (this file)
│
└── README.md
```

---

## Model Performance

| Metric | Tool Wear (VB) | RUL Estimation |
|--------|----------------|----------------|
| **R² Score** | **0.9357 (93.6%)** | **0.9039 (90.4%)** |
| MAE | 0.0238 mm | 4.86 min |
| RMSE | 0.0394 mm | — |

---

## API Endpoints

### 1. POST `/predict`
**Main endpoint — send sensor readings, get tool health back.**

```json
// Request Body
{
  "smcAC_mean": 1.85,
  "smcAC_rms": 1.87,
  "smcAC_std": 0.12,
  "smcDC_mean": 6.20,
  "smcDC_rms": 6.21,
  "smcDC_std": 0.08,
  "vib_table_mean": 0.92,
  "vib_table_rms": 0.94,
  "vib_spindle_mean": 4.10,
  "vib_spindle_rms": 4.15,
  "AE_table_mean": 0.22,
  "AE_table_rms": 0.23,
  "AE_spindle_mean": 0.31,
  "AE_spindle_rms": 0.32,
  "time": 25.0,
  "DOC": 0.75,
  "feed": 0.5,
  "material": 1,
  "VB_lag1": 0.18,
  "VB_lag2": 0.14,
  "run_norm": 0.5
}

// Response
{
  "VB_Predicted": 0.2187,
  "RUL_Predicted": 14.32,
  "Tool_Health_Score": "27.1%",
  "Wear_Level": "High",
  "Maintenance_Action": "Inspect",
  "Confidence_Score": "93.6%",
  "Next_Inspection": "5.7 min",
  "model_used": "Gradient Boosting",
  "wear_limit_mm": 0.3
}
```

### 2. GET `/health`
```json
{ "status": "ok", "model": "Gradient Boosting" }
```

### 3. GET `/model/info`
```json
{
  "model_name": "Gradient Boosting",
  "feature_count": 56,
  "wear_limit_mm": 0.3,
  "vb_r2": 0.9357,
  "vb_mae_mm": 0.0238,
  "rul_r2": 0.9039,
  "rul_mae_min": 4.8607
}
```

---

## Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Swagger UI auto-generated at: http://localhost:8000/docs

---

## Output Columns Explained (for UI Dashboard)

| Column | Type | Meaning | UI Suggestion |
|--------|------|---------|---------------|
| `VB_Predicted` | float (mm) | Actual flank wear amount | Progress bar 0–0.3 mm |
| `RUL_Predicted` | float (min) | Minutes until tool needs replacing | Countdown timer |
| `Tool_Health_Score` | string % | Tool remaining life (100%=new) | Circular gauge |
| `Wear_Level` | Low/Medium/High/Critical | Categorical state | Color badge 🟢🟡🟠🔴 |
| `Maintenance_Action` | string | What operator should do NOW | Alert card |
| `Confidence_Score` | string % | Model's confidence in prediction | Small badge |
| `Next_Inspection` | string (min) | When to check again | Scheduled timer |

---

## Wear Level Thresholds

| Level | VB Range | Color |
|-------|----------|-------|
| Low | 0 – 0.12 mm | 🟢 Green |
| Medium | 0.12 – 0.21 mm | 🟡 Yellow |
| High | 0.21 – 0.30 mm | 🟠 Orange |
| Critical | > 0.30 mm | 🔴 Red |
