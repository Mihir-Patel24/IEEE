"""
test_full_system.py - End-to-end integration test for the Full project
"""
import sys
import os

sys.path.insert(0, r'd:\IEEE\Full')

errors = []

# ── Test 1: decision_engine ───────────────────────────────────────────────────
try:
    from decision_engine.decision_engine import DecisionFusionEngine
    print('[OK] decision_engine.DecisionFusionEngine')
except Exception as e:
    errors.append(f'[FAIL] decision_engine: {e}')

# ── Test 2: AI4I model ────────────────────────────────────────────────────────
try:
    from Predictive_Maintenance_Project.predict_unified import predict as predict_ai4i
    print('[OK] predict_unified (AI4I model)')
except Exception as e:
    errors.append(f'[FAIL] predict_unified: {e}')

# ── Test 3: PredictionService (loads all 3 layers) ────────────────────────────
try:
    from services.prediction_service import PredictionService
    svc = PredictionService()
    print('[OK] PredictionService (all 3 models loaded)')
except Exception as e:
    errors.append(f'[FAIL] PredictionService: {e}')
    svc = None

if errors:
    print()
    for e in errors:
        print(e)
    sys.exit(1)

# ── Test 4: Full end-to-end prediction ───────────────────────────────────────
print()
print('[RUNNING] Full end-to-end prediction (critical scenario)...')

payload = {
    # NASA milling sensor inputs
    'smcAC_mean': 3.80, 'smcAC_rms': 3.85, 'smcAC_std': 0.40,
    'smcDC_mean': 8.50, 'smcDC_rms': 8.55, 'smcDC_std': 0.30,
    'vib_table_mean': 2.10, 'vib_table_rms': 2.20,
    'vib_spindle_mean': 7.50, 'vib_spindle_rms': 7.60,
    'AE_table_mean': 0.55, 'AE_table_rms': 0.58,
    'AE_spindle_mean': 0.65, 'AE_spindle_rms': 0.68,
    'time': 180.0, 'DOC': 1.5, 'feed': 0.8, 'material': 3,
    'VB_lag1': 0.38, 'VB_lag2': 0.35, 'run_norm': 0.95,
    # AI4I machine inputs
    'air_temp': 299.0, 'proc_temp': 309.5, 'rpm': 2861,
    'torque': 4.6, 'tool_wear': 143, 'machine_type': 'L',
}

result = svc.predict(payload)

print()
print('  --- FUSED DECISION OUTPUT ---')
for key in ['overall_risk', 'overall_status', 'maintenance_priority',
            'overall_machine_status', 'tool_health', 'machine_health',
            'failure_probability', 'failure_type', 'estimated_downtime',
            'estimated_cost_saving', 'next_maintenance']:
    val = result.get(key, 'N/A')
    print(f'  {key:<30}: {val}')

actions = result.get('recommended_actions', [])
print(f'  {"recommended_actions":<30}: {actions[0] if actions else "N/A"}')
if len(actions) > 1:
    for a in actions[1:3]:
        print(f'  {"  +":<30}  {a}')

print()
print('[PASS] All imports and full prediction pipeline working.')
print('[READY] Run:  streamlit run d:/IEEE/Full/dashboard/app.py')
