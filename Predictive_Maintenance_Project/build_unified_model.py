
"""
UNIFIED Predictive Maintenance Model
Combines machine_failure_model + failure_type_model into ONE bundle
Adds 7 enriched operator-friendly output fields.

Saves: predictive_maintenance_model.pkl
"""

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score

BASE = r'd:\IEEE\Predictive_Maintenance_Project'
DATA = os.path.join(BASE, 'dataset', 'ai4i2020.csv')
OUT  = os.path.join(BASE, 'outputs')
MDL  = os.path.join(BASE, 'models')

# ── FEATURE ENGINEERING ───────────────────────────────────────
df = pd.read_csv(DATA)

df['Torque_Wear']     = df['Torque [Nm]'] * df['Tool wear [min]']
df['Power']           = (2 * np.pi * df['Rotational speed [rpm]'] * df['Torque [Nm]']) / 60
df['Heat_Index']      = df['Process temperature [K]'] - df['Air temperature [K]']
df['Temp_Difference'] = df['Process temperature [K]'] - df['Air temperature [K]']
df['Type_L']          = (df['Type'] == 'L').astype(int)
df['Type_M']          = (df['Type'] == 'M').astype(int)

FEATURES = [
    'Torque_Wear', 'Power', 'Rotational speed [rpm]', 'Torque [Nm]',
    'Heat_Index', 'Temp_Difference', 'Tool wear [min]',
    'Type_L', 'Type_M', 'Air temperature [K]', 'Process temperature [K]'
]

def get_failure_type(row):
    if row['TWF']: return 'TWF'
    if row['HDF']: return 'HDF'
    if row['PWF']: return 'PWF'
    if row['OSF']: return 'OSF'
    if row['RNF']: return 'RNF'
    return 'No Failure'

df['Failure_Type'] = df.apply(get_failure_type, axis=1)

X          = df[FEATURES]
y_failure  = df['Machine failure']
y_type     = df['Failure_Type']

# ── TRAIN/TEST ────────────────────────────────────────────────
X_tr, X_te, yf_tr, yf_te = train_test_split(
    X, y_failure, test_size=0.2, random_state=42, stratify=y_failure)
_, _,        yt_tr, yt_te = train_test_split(
    X, y_type,    test_size=0.2, random_state=42, stratify=y_failure)

# ── MODEL 1: Machine Failure ──────────────────────────────────
m1 = RandomForestClassifier(n_estimators=300, max_depth=12,
                             min_samples_leaf=2, class_weight='balanced',
                             random_state=42, n_jobs=-1)
m1.fit(X_tr, yf_tr)
yf_pred = m1.predict(X_te)
yf_prob = m1.predict_proba(X_te)[:, 1]
acc1    = accuracy_score(yf_te, yf_pred)
auc1    = roc_auc_score(yf_te, yf_prob)
print(f"  Machine Failure   | Accuracy: {acc1*100:.2f}%  AUC: {auc1:.4f}")

# ── MODEL 2: Failure Type ─────────────────────────────────────
m2 = RandomForestClassifier(n_estimators=300, max_depth=14,
                             min_samples_leaf=1, class_weight='balanced',
                             random_state=42, n_jobs=-1)
m2.fit(X_tr, yt_tr)
yt_pred = m2.predict(X_te)
acc2    = accuracy_score(yt_te, yt_pred)
print(f"  Failure Type      | Accuracy: {acc2*100:.2f}%")


# ── UNIFIED BUNDLE ────────────────────────────────────────────
UNIFIED_BUNDLE = {
    # Both models
    'failure_model':     m1,
    'failure_type_model': m2,
    # Metadata
    'features':          FEATURES,
    'failure_classes':   ['No Failure', 'Failure'],
    'type_classes':      list(m2.classes_),
    'model_version':     '2.0',
    # Performance
    'failure_accuracy':  acc1,
    'failure_auc':       auc1,
    'type_accuracy':     acc2,
    # Interpretation logic (embedded for UI)
    'severity_thresholds': {
        'Healthy':   (0,   20),
        'Warning':   (20,  50),
        'High Risk': (50,  80),
        'Critical':  (80, 100),
    },
    'component_map': {
        'TWF':        ['Tool Holder', 'Cutting Tool', 'Tool Clamp'],
        'HDF':        ['Cooling System', 'Coolant Pump', 'Heat Exchanger'],
        'PWF':        ['Motor', 'Power Supply', 'Electrical Wiring'],
        'OSF':        ['Spindle', 'Bearings', 'Drive Shaft'],
        'RNF':        ['Complete Machine Inspection Required'],
        'No Failure': ['Routine Check — All Systems Normal'],
    },
    'action_map': {
        'Healthy':   'Continue Production',
        'Warning':   'Reduce Load',
        'High Risk': 'Schedule Maintenance',
        'Critical':  'Stop Machine Immediately',
    },
    'window_map': {
        'Healthy':   'Within 24 Hours (Routine)',
        'Warning':   'Within 8 Hours',
        'High Risk': 'Within 2 Hours',
        'Critical':  'IMMEDIATELY',
    },
    'priority_map': {
        'Healthy':   'Low',
        'Warning':   'Medium',
        'High Risk': 'High',
        'Critical':  'Immediate',
    },
    'status_map': {
        'Healthy':   'Running Normally',
        'Warning':   'Operating with Risk',
        'High Risk': 'Critical — Attention Required',
        'Critical':  'Shutdown Required',
    },
}

path = os.path.join(MDL, 'predictive_maintenance_model.pkl')
joblib.dump(UNIFIED_BUNDLE, path)
print(f"\n  Saved -> {path}")
print(f"  Size  -> {os.path.getsize(path)/1024:.0f} KB")
