# Hybrid AI-Based Predictive Maintenance Framework for Smart Manufacturing

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.9-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**An enterprise-grade AI platform that fuses NASA Tool Wear predictions with AI4I 2020 failure detection through a custom Decision Fusion Layer — deployed as a production Streamlit SaaS dashboard.**

[Live Demo](#) · [Architecture](#architecture) · [Setup](#setup) · [Features](#features)

</div>

---

## Overview

This project implements a **Hybrid AI-Based Predictive Maintenance Framework** that integrates two independent machine learning models through a novel **Decision Fusion Engine** to deliver unified, high-confidence maintenance recommendations for smart manufacturing environments.

> **Research Context**: IEEE Conference 2025 — VIT & MIT Collaboration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    IndustrialMaint AI Platform                   │
│                         Streamlit v3.0                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
┌─────────▼─────────┐               ┌──────────▼──────────┐
│   MODULE 1        │               │   MODULE 2           │
│   NASA Milling    │               │   AI4I 2020          │
│   Dataset         │               │   Dataset            │
│                   │               │                      │
│ • Tool Wear (VB)  │               │ • Machine Failure    │
│ • RUL Prediction  │               │ • Failure Type       │
│ • Tool Health %   │               │ • Failure Prob %     │
│                   │               │ • Machine Health %   │
└─────────┬─────────┘               └──────────┬──────────┘
          │                                     │
          └──────────────┬──────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  DECISION FUSION    │
              │     ENGINE          │
              │                     │
              │ • Risk Fusion       │
              │ • Priority Scoring  │
              │ • Recommendations   │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │     DATABASE        │
              │  Supabase/SQLite    │
              │                     │
              │ • Prediction Logs   │
              │ • User Sessions     │
              │ • Audit Trail       │
              └─────────────────────┘
```

---

## Features

### 🤖 AI/ML Modules
| Feature | Dataset | Output |
|---------|---------|--------|
| Tool Wear Prediction | NASA Milling (mill.mat) | VB in mm |
| Remaining Useful Life | NASA Milling | Minutes remaining |
| Tool Health Score | Derived | 0–100% |
| Machine Failure Detection | AI4I 2020 | Yes/No |
| Failure Probability | AI4I 2020 | 0–100% |
| Failure Type Classification | AI4I 2020 | TWF/HDF/PWF/OSF/RNF |
| Machine Health Score | Derived | 0–100% |

### 🔮 Decision Fusion Layer
- Weighted risk score combining both models
- Overall machine status: Healthy / Warning / High Risk / Critical
- Maintenance priority: Low / Medium / High / Immediate
- Explainable risk breakdown per factor

### 🖥️ Enterprise Dashboard
- Premium industrial UI (Siemens / GE Digital inspired)
- Real-time KPI cards with trend sparklines
- Digital Twin component status visualization
- AI Insights panel with recommended actions
- Decision Fusion workflow diagram
- Dark / Light mode toggle

### 📊 Analytics & Reports
- Prediction history with search & filter
- PDF report generation (per prediction)
- CSV export for batch analysis
- Cost & ROI calculator
- Maintenance Gantt timeline

### 🗂 Machine Registry (Phase 3)
| Feature | Notes |
|---|---|
| Register machines | Machine ID, name, type, material, factory, location |
| Edit inline | All fields editable per-row |
| Status toggle | Active / Idle / Maintenance / Offline (live update) |
| Delete with confirm | Role-guarded: Admin & Plant Manager only |
| Fleet KPI cards | Total / Active / In Maintenance / Offline counts |
| Audit trail | Every change logged to `audit_logs` |

### 🗄 Database (Phase 3)
| Feature | Notes |
|---|---|
| SQLite local mode | Zero-config, auto-init tables |
| Supabase PostgreSQL | Set `SUPABASE_URL` env var to switch |
| Schema migration | `database/supabase_schema.sql` — run in Supabase SQL Editor |
| Row Level Security | All 7 tables have RLS; users see only their data |
| Helper views | `v_user_prediction_stats`, `v_user_alert_summary` |
| DB health indicator | Mode + prediction/machine counts shown in sidebar |

### 🔐 Authentication & Security
| Feature | Status | Notes |
|---|---|---|
| Demo Login | ✅ | `demo@industrialmaint.ai` / `Demo@1234` |
| User Registration | ✅ | Full name, company, factory, department, role |
| Password Hashing | ✅ | SHA-256 with secret salt |
| Forgot Password | ✅ | Token-based reset (1hr expiry) |
| Change Password | ✅ | Via user profile (current pw required) |
| Session Timeout | ✅ | Configurable via `SESSION_TIMEOUT_HOURS` env |
| Audit Logging | ✅ | Every login, logout, reset, profile change |
| Supabase Auth | 🔄 | Ready — set `SUPABASE_URL` to activate |

#### 🛡️ Role-Based Access Control (RBAC)
| Role | Dashboard | Predictions | Reports | Cost Analysis | Settings | Admin Panel |
|---|---|---|---|---|---|---|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ Edit | ✅ |
| **Plant Manager** | ✅ | ✅ | ✅ Export | ✅ | ✅ Edit | ❌ |
| **Maintenance Engineer** | ✅ | ✅ | ✅ View | ❌ | ✅ View | ❌ |
| **Operator** | ✅ | ❌ | ❌ | ❌ | ✅ View | ❌ |

---

## Project Structure

```
Hybrid-AI-Based-Predictive-Maintenance-Framework/
│
├── dashboard/                  # Streamlit enterprise frontend
│   ├── app.py                  # Entry point, auth gate, session timeout
│   ├── components.py           # Reusable UI component library (v4)
│   ├── style.css               # Premium CSS design system
│   ├── api_client.py           # Frontend ↔ backend bridge
│   ├── auth/                   # Authentication service
│   │   ├── auth_service.py     # Login, register, logout, session mgmt
│   │   └── rbac.py             # Role-based access control & permissions
│   ├── config/                 # App configuration
│   ├── database/               # DB client (SQLite/Supabase dual-mode)
│   ├── utils/                  # PDF generator, helpers
│   └── views/                  # Page modules
│       ├── dashboard.py        # Operations control center
│       ├── predictions.py      # AI prediction engine UI
│       ├── machine_health.py   # Digital twin fleet view
│       ├── maintenance.py      # Maintenance scheduler
│       ├── reports.py          # Reports & PDF export
│       ├── cost_analysis.py    # ROI calculator
│       ├── profile.py          # User profile + change password
│       ├── settings.py         # Platform settings (RBAC-aware)
│       ├── login.py            # Enterprise login page
│       ├── register.py         # User registration
│       ├── forgot_password.py  # Token-based password reset
│       └── machine_registry.py # Fleet Registry CRUD (Phase 3)
│
├── database/                   # Schema & migrations
│   └── supabase_schema.sql     # PostgreSQL schema with RLS (Phase 3)
│
├── services/                   # ML inference services
│   ├── prediction_service.py   # Main orchestrator
│   ├── input_mapper.py         # Operator input → ML features
│   ├── predict_tool_wear.py    # NASA tool wear inference
│   └── predict_ai4i.py         # AI4I failure inference
│
├── decision_engine/            # ⭐ Core research contribution
│   ├── decision_engine.py      # Decision Fusion Engine
│   ├── fusion.py               # Risk fusion algorithms
│   ├── recommendation.py       # Action recommendations
│   ├── config.py               # Fusion weights & thresholds
│   └── utils.py                # Shared utilities
│
├── models/                     # Trained model artifacts
│   ├── tool_wear_model.pkl     # NASA Milling GBM model
│   ├── predictive_maintenance_model.pkl  # AI4I Random Forest
│   └── __init__.py             # Unified model loader
│
├── data/                       # Datasets
│   └── ai4i2020.csv            # AI4I 2020 Predictive Maintenance Dataset
│
├── docs/                       # Documentation
│   └── System_Architecture.docx
│
├── notebooks/                  # Research Jupyter notebooks
│
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git exclusions
└── README.md                   # This file
```

---

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Mihir-Patel24/Hybrid-AI-Based-Predictive-Maintenance-Framework-for-Smart-Manufacturing.git
cd Hybrid-AI-Based-Predictive-Maintenance-Framework-for-Smart-Manufacturing
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional for Demo)
```bash
cp .env.example .env
# Edit .env with your Supabase credentials if using cloud mode
```

### 5. Run the Dashboard
```bash
streamlit run dashboard/app.py
```

### 6. Login
| Mode | Email | Password |
|------|-------|----------|
| **Demo** | `demo@industrialmaint.ai` | `Demo@1234` |
| **Production** | Your Supabase account | — |

---

## Deployment

### Streamlit Community Cloud
1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path**: `dashboard/app.py`
5. Add secrets in the Streamlit dashboard:
```toml
[supabase]
url = "your-supabase-url"
anon_key = "your-anon-key"

[app]
secret_key = "your-secret-key"
```

---

## Models

### NASA Milling Tool Wear Model
- **Dataset**: NASA Milling Dataset (mill.mat) — 167 experiments
- **Algorithm**: Gradient Boosting Regressor
- **Features**: 21 sensor signals (spindle current, vibration, acoustic emission)
- **Target**: Flank wear (VB) in mm
- **Derived Outputs**: RUL (minutes), Tool Health Score (%)

### AI4I 2020 Machine Failure Model
- **Dataset**: AI4I 2020 (10,000 data points)
- **Algorithm**: Random Forest Classifier
- **Features**: Air temp, Process temp, RPM, Torque, Tool wear, Machine type
- **Target**: Machine failure (binary) + failure type (5-class)

### Decision Fusion Engine ⭐
The core research contribution — a weighted risk fusion algorithm that:
1. Combines tool wear risk score with machine failure probability
2. Applies domain-expert weights per failure mode
3. Outputs a unified Overall Risk Score (0–100)
4. Generates priority-ranked maintenance recommendations

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.40+ |
| Styling | Custom CSS (Industrial Design System) |
| ML Models | scikit-learn 1.9 |
| Data Processing | NumPy, Pandas |
| Visualization | Plotly 5.20+ |
| Database | Supabase PostgreSQL / SQLite (local) |
| Authentication | Supabase Auth / Demo mode |
| PDF Reports | fpdf2 |
| Deployment | Streamlit Community Cloud |

---

## Research Team

- **Institution**: VIT (Vellore Institute of Technology) & MIT
- **Conference**: IEEE 2025
- **Domain**: Smart Manufacturing, Predictive Maintenance, AI/ML

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <b>IndustrialMaint AI v3.0</b> · Built for IEEE Research 2025
</div>
