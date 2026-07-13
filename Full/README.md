# Predictive Maintenance System
### AI-Powered Tool Wear & Machine Failure Prediction

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [How to Run](#how-to-run)
4. [How the Model Works](#how-the-model-works)
5. [Data Flow: Frontend to Model to Output](#data-flow-frontend-to-model-to-output)
6. [API Endpoints](#api-endpoints)
7. [Dashboard Pages](#dashboard-pages)
8. [Test Inputs](#test-inputs)
9. [Troubleshooting](#troubleshooting)

---

## Project Overview

This system predicts **tool wear (VB in mm)** and **remaining useful life (RUL in minutes)** for CNC milling machines using sensor data from the NASA Milling dataset. It also provides machine failure risk classification using the AI4I 2020 dataset.

| Component | Technology |
|---|---|
| ML Model | Gradient Boosting (scikit-learn 1.9.0) |
| Backend API | FastAPI + Uvicorn |
| Frontend Dashboard | Streamlit |
| Data | NASA Milling Dataset + AI4I 2020 |
| Explainability | SHAP values |

---

## Project Structure

```
IEEE-main/
|-- dashboard/                  # Streamlit frontend
|   |-- app.py                  # Main entry point
|   |-- api_client.py           # Connects frontend to backend
|   |-- utils.py                # Chart helpers (Plotly)
|   |-- style.css               # Dashboard styling
|   |-- views/                  # One file per page
|   |   |-- dashboard.py        # Main dashboard page
|   |   |-- tool_wear.py        # Tool Wear Prediction page
|   |   |-- rul.py              # RUL Estimation page
|   |   |-- failure.py          # Failure Prediction page
|   |   |-- data_input.py       # CSV upload + manual input
|   |   |-- sensor_data.py      # Live sensor charts
|   |   |-- alerts.py           # Alerts & Notifications
|   |   |-- maintenance.py      # Maintenance Recommendations
|   |   |-- reports.py          # Download reports
|   |   |-- shap_page.py        # SHAP explainability
|   |   |-- settings.py         # Settings
|   |   `-- help_page.py        # Help & FAQ
|
|-- tool-wear-ai/               # ML backend
|   |-- backend/
|   |   |-- main.py             # FastAPI server (POST /predict)
|   |   |-- predict.py          # Direct Python prediction (no server needed)
|   |   `-- model/
|   |       `-- best_model.pkl  # Trained Gradient Boosting model bundle
|   |-- data/
|   |   `-- processed/
|   |       `-- master_features.csv   # Engineered features from NASA dataset
|   |-- ml/scripts/
|   |   `-- pipeline.py         # Full ML training pipeline
|   `-- outputs/
|       `-- predictions/
|           `-- predictions_enhanced.csv  # Test set predictions
|
|-- retrain_model.py            # Retrain model with current scikit-learn
|-- start_backend.bat           # One-click backend start
`-- start_dashboard.bat         # One-click dashboard start
```

---

## How to Run

### Prerequisites
```
Python 3.10+
Virtual environment at: IEEE-main/venv/
```

### Step 1 — Activate virtual environment
```bash
cd D:\IEEE_Research_Internship\IEEE-main
venv\Scripts\activate
```

### Step 2 — Install dependencies
```bash
# Backend
pip install -r tool-wear-ai/backend/requirements.txt

# Dashboard
pip install -r dashboard/requirements.txt
```

### Step 3 — Retrain model (first time only)
```bash
python retrain_model.py
```
This reads `master_features.csv`, trains Gradient Boosting models for VB and RUL,
and saves `tool-wear-ai/backend/model/best_model.pkl`.

### Step 4 — Start Backend API (Terminal 1)
```bash
# Option A: Use batch file
start_backend.bat

# Option B: Manual
cd tool-wear-ai/backend
uvicorn main:app --reload --port 8000
```
API will be live at: `http://localhost:8000`
Swagger docs at: `http://localhost:8000/docs`

### Step 5 — Start Dashboard (Terminal 2)
```bash
# Option A: Use batch file
start_dashboard.bat

# Option B: Manual
cd dashboard
streamlit run app.py --server.port 8501
```
Dashboard will open at: `http://localhost:8501`

> **Note:** The dashboard works even WITHOUT the backend running.
> It automatically falls back to calling `predict.py` directly (local mode).
> The header shows a green dot (API Online) or red dot (API Offline / local mode).

---

## How the Model Works

### Datasets
| Dataset | Purpose | Records | Target |
|---|---|---|---|
| NASA Milling | Tool wear regression | 167 engineered rows | VB (mm) |
| AI4I 2020 | Machine failure classification | 10,000 rows | Machine Failure (0/1) |

### Feature Engineering (NASA Milling)
Raw sensor signals are aggregated per `(case, run)` into statistical features:

```
For each sensor [smcAC, smcDC, vib_table, vib_spindle, AE_table, AE_spindle]:
    - mean, std, rms, max, min, var, skew, kurtosis  (8 stats x 6 sensors = 48 features)

Machining parameters:
    - time, DOC (depth of cut), feed, material_enc, run_norm

Lag features (temporal context):
    - VB_lag1  (previous VB reading)
    - VB_lag2  (two readings ago)
    - VB_diff  (VB_lag1 - VB_lag2, wear rate proxy)

Total: 56 features
```

### Model Architecture
```
Input (56 features)
    |
    v
SimpleImputer (median strategy)   -- fills any missing sensor values
    |
    v
RobustScaler                      -- scales features, robust to outliers
    |
    v
GradientBoostingRegressor         -- predicts VB (tool wear in mm)
    |
    v
GradientBoostingRegressor         -- predicts RUL (remaining useful life in min)
```

### Model Performance (Test Set)
| Metric | VB Model | RUL Model |
|---|---|---|
| R² Score | 0.9077 | 0.7407 |
| MAE | 0.0463 mm | 11.52 min |
| Wear Limit | 0.30 mm | — |

### Interpretation Logic
After prediction, the system computes:

```python
wear_ratio = VB_predicted / wear_limit (0.30 mm)

Tool Health  = (1 - wear_ratio) * 100 %
Failure Risk = wear_ratio * 100 %

Wear Level:
    wear_ratio < 0.40  ->  "Low"
    wear_ratio < 0.70  ->  "Medium"
    wear_ratio < 1.00  ->  "High"
    wear_ratio >= 1.00 ->  "Critical"

Maintenance Action:
    wear_ratio >= 1.00 ->  "REPLACE NOW"
    wear_ratio >= 0.85 ->  "Schedule Replace"
    wear_ratio >= 0.60 ->  "Inspect"
    else               ->  "Continue"
```

---

## Data Flow: Frontend to Model to Output

```
USER fills Input Parameters form in Dashboard
        |
        | (Material, DOC, Feed, Time, VB lags, Sensor readings)
        v
dashboard/views/dashboard.py  [predict_clicked handler]
        |
        | builds payload dict matching SensorInput schema
        v
dashboard/api_client.py  [predict(payload)]
        |
        |-- Try 1: POST http://localhost:8000/predict  (FastAPI REST API)
        |       |
        |       v
        |   tool-wear-ai/backend/main.py  [POST /predict endpoint]
        |       |
        |       v
        |   build_feature_vector(inp)
        |       - maps 21 input fields to 56 feature columns
        |       - fills missing features with training-data medians
        |       - applies Imputer + Scaler from saved bundle
        |       |
        |       v
        |   VB_MODEL.predict(X)   -> VB_Predicted (mm)
        |   RUL_MODEL.predict(X)  -> RUL_Predicted (min)
        |       |
        |       v
        |   Returns PredictionResponse JSON
        |
        |-- Try 2 (if API offline): import predict.py directly
        |       tool-wear-ai/backend/predict.py [predict_single(**kwargs)]
        |       Same logic, no HTTP overhead
        |
        v
dashboard/api_client.py  [parse_prediction(result)]
        |
        | Normalises response into session_state.prediction dict:
        | { vb, rul, tool_health, failure_risk, machine_status,
        |   wear_level, action, confidence, next_inspection }
        |
        v
dashboard/views/dashboard.py  [st.session_state.prediction updated]
        |
        v
ALL 5 KPI CARDS update:
    - Tool Health %
    - Failure Risk %
    - Remaining Useful Life
    - Machine Status
    - Active Alerts count

ALL 3 CHART PANELS update:
    - Tool Wear chart (VB vs threshold)
    - RUL projection chart
    - Failure Risk gauge

MAINTENANCE RECOMMENDATION updates:
    - Recommendation text
    - Reason
    - Confidence score
    - Next inspection time
```

### Input Fields Explained

| Field | Description | Typical Range |
|---|---|---|
| Material Type | 1=Cast Iron, 2=Steel | 1 or 2 |
| Depth of Cut (mm) | Axial depth of cut | 0.75 – 1.5 mm |
| Feed Rate (mm/rev) | Tool feed per revolution | 0.25 – 0.75 mm/rev |
| Machining Time (min) | Elapsed time in current run | 0 – 50 min |
| VB Lag 1 (mm) | Previous tool wear reading | 0.0 – 0.30 mm |
| VB Lag 2 (mm) | Tool wear two readings ago | 0.0 – 0.30 mm |
| Run Position [0-1] | Normalised position in experiment | 0.0 – 1.0 |
| smcAC mean | Spindle AC current mean | -0.5 – 2.5 A |
| smcDC mean | Spindle DC current mean | 4.0 – 10.0 A |
| vib_table mean | Table vibration mean | 0.5 – 2.0 g |
| vib_spindle mean | Spindle vibration mean | 0.2 – 1.0 g |
| AE_table mean | Acoustic emission table mean | 0.1 – 0.5 V |
| AE_spindle mean | Acoustic emission spindle mean | 0.1 – 0.5 V |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Server health check |
| GET | `/model/info` | Model name, R², MAE, feature count |
| POST | `/predict` | Predict VB + RUL from sensor input |

### POST /predict — Request Body
```json
{
  "smcAC_mean": -0.165,
  "smcAC_rms": 1.85,
  "smcAC_std": 0.12,
  "smcDC_mean": 6.20,
  "smcDC_rms": 6.21,
  "smcDC_std": 0.08,
  "vib_table_mean": 0.92,
  "vib_table_rms": 0.94,
  "vib_spindle_mean": 0.40,
  "vib_spindle_rms": 0.41,
  "AE_table_mean": 0.22,
  "AE_table_rms": 0.23,
  "AE_spindle_mean": 0.31,
  "AE_spindle_rms": 0.32,
  "time": 25.0,
  "DOC": 0.75,
  "feed": 0.5,
  "material": 1,
  "VB_lag1": 0.0,
  "VB_lag2": 0.0,
  "run_norm": 0.5
}
```

### POST /predict — Response
```json
{
  "VB_Predicted": 0.1791,
  "RUL_Predicted": 36.46,
  "Tool_Health_Score": "40.3%",
  "Wear_Level": "Medium",
  "Maintenance_Action": "Continue",
  "Confidence_Score": "87.1%",
  "Next_Inspection": "21.9 min",
  "model_used": "Gradient Boosting",
  "wear_limit_mm": 0.3
}
```

---

## Dashboard Pages

| Page | What it does |
|---|---|
| Dashboard | Main overview — KPIs, charts, input form, SHAP, recommendation |
| Tool Wear Prediction | Detailed VB prediction with history table |
| RUL Estimation | RUL projection chart with recalculation slider |
| Failure Prediction | Failure risk gauge + confusion matrix + AI4I form |
| Data Input | Upload CSV for batch prediction or manual entry |
| Sensor Data | Live-style 6-sensor charts with statistics |
| Alerts & Notifications | Alert list with custom alert creation |
| Maintenance Recommendations | Schedule + cost savings estimate |
| Reports | Summary table + TXT/CSV download |
| Explainability (SHAP) | Feature importance bar chart + beeswarm plot |
| Settings | Thresholds, notifications, model selection |
| Help | FAQ + quick navigation guide |

---

## Test Inputs

### Test 1 — Healthy Tool (Low Wear)
```
Material: Cast Iron (1) | DOC: 1.5 | Feed: 0.5 | Time: 4.0
VB Lag 1: 0.0 | VB Lag 2: 0.0 | Run Position: 0.12
smcAC mean: -0.166 | smcDC mean: 5.566
vib_table mean: 1.543 | vib_spindle mean: 0.549
AE_table mean: 0.174 | AE_spindle mean: 0.188

Expected: VB ~ 0.09-0.12 mm | Wear Level: Low | Action: Continue
```

### Test 2 — Moderate Wear
```
Material: Cast Iron (1) | DOC: 1.5 | Feed: 0.5 | Time: 19.0
VB Lag 1: 0.20 | VB Lag 2: 0.155 | Run Position: 0.41
smcAC mean: -0.158 | smcDC mean: 7.491
vib_table mean: 1.495 | vib_spindle mean: 0.401
AE_table mean: 0.187 | AE_spindle mean: 0.286

Expected: VB ~ 0.22-0.26 mm | Wear Level: High | Action: Inspect
```

### Test 3 — Critical Wear (End of Life)
```
Material: Cast Iron (1) | DOC: 1.5 | Feed: 0.5 | Time: 35.0
VB Lag 1: 0.38 | VB Lag 2: 0.29 | Run Position: 0.71
smcAC mean: -0.154 | smcDC mean: 8.018
vib_table mean: 1.142 | vib_spindle mean: 0.446
AE_table mean: 0.264 | AE_spindle mean: 0.343

Expected: VB ~ 0.38-0.45 mm | Wear Level: Critical | Action: REPLACE NOW
```

---

## Troubleshooting

### Blank page in browser
```bash
# Kill old Streamlit processes
taskkill /f /im streamlit.exe

# Clear Python cache
cd dashboard
rmdir /s /q views\__pycache__
rmdir /s /q __pycache__

# Restart
..\venv\Scripts\streamlit run app.py
```

### ModuleNotFoundError: No module named '_loss'
The model was saved with an older scikit-learn. Retrain it:
```bash
python retrain_model.py
```

### UnicodeDecodeError: 'charmap' codec
All files use UTF-8. Open CSS with explicit encoding:
```python
open("style.css", encoding="utf-8")
```

### API shows red dot (offline)
The dashboard still works in local mode — it imports `predict.py` directly.
To start the API:
```bash
start_backend.bat
```

### Port already in use
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Kill process on port 8501
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

---

## Team

| Member | Role |
|---|---|
| Member 1 | AI/ML Model Engineer — Gradient Boosting, XGBoost, model comparison |
| Member 2 | Data & Explainability Engineer — SHAP, feature engineering |
| Member 3 | Full-Stack & Dashboard Developer — Streamlit dashboard |
| Member 4 | Research, Integration & Documentation Lead — IEEE paper, pipeline |

---

*VIT Group 18 | IEEE Research Internship 2025*
