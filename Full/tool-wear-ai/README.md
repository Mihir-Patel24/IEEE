# Tool Wear AI — Predictive Maintenance System

AI-powered tool wear (VB) prediction and Remaining Useful Life (RUL) estimation
using the NASA Ames Milling Dataset.

**Model:** Gradient Boosting | **VB Accuracy:** 93.6% R² | **RUL Accuracy:** 90.4% R²

---

## Quick Start

### Backend (Python API)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Run a Single Prediction (Python)
```python
from backend.predict import predict_single

result = predict_single(
    smcAC_mean=1.85, smcAC_rms=1.87, smcAC_std=0.12,
    smcDC_mean=6.20, smcDC_rms=6.21, smcDC_std=0.08,
    vib_table_mean=0.92, vib_table_rms=0.94,
    vib_spindle_mean=4.10, vib_spindle_rms=4.15,
    AE_table_mean=0.22, AE_table_rms=0.23,
    AE_spindle_mean=0.31, AE_spindle_rms=0.32,
    time=25.0, VB_lag1=0.18, VB_lag2=0.14
)
print(result["Maintenance_Action"])  # "Inspect"
print(result["Tool_Health_Score"])   # "27.1%"
```

### Retrain the Model
```bash
cd ml/scripts
python pipeline.py
# Outputs saved to outputs/
```

---

## Project Structure

```
tool-wear-ai/
├── backend/        REST API + model loading
├── data/           Raw + processed datasets
├── ml/             Training pipeline
├── outputs/        Plots + predictions
└── docs/           API documentation
```

See `docs/API.md` for full endpoint documentation and UI integration guide.

---

## Dataset

- **Source:** NASA Ames Milling Dataset (mill.mat)
- **Experiments:** 16 machining cases
- **Sensors:** Spindle Current (AC/DC), Table Vibration, Spindle Vibration, AE Table, AE Spindle
- **Features:** 56 (8 statistics × 6 sensors + 8 machining/lag features)
- **Target 1:** Flank Wear VB (mm)
- **Target 2:** Remaining Useful Life (minutes)
