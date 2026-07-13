
"""
predict_unified.py
==================
Single importable module for the unified Predictive Maintenance model.

Usage:
    from predict_unified import predict, predict_batch

    result = predict(
        air_temp=298.1, proc_temp=308.6,
        rpm=1551, torque=42.8,
        tool_wear=150, machine_type='M'
    )
    print(result)
"""

import joblib
import numpy as np
import pandas as pd
import os

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'predictive_maintenance_model.pkl')
_BUNDLE = None


def _load():
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = joblib.load(_MODEL_PATH)


def _build_row(air_temp, proc_temp, rpm, torque, tool_wear, machine_type='M'):
    torque_wear = torque * tool_wear
    power       = (2 * np.pi * rpm * torque) / 60
    heat        = proc_temp - air_temp
    return pd.DataFrame([{
        'Torque_Wear':             torque_wear,
        'Power':                   power,
        'Rotational speed [rpm]':  rpm,
        'Torque [Nm]':             torque,
        'Heat_Index':              heat,
        'Temp_Difference':         heat,
        'Tool wear [min]':         tool_wear,
        'Type_L':                  1 if machine_type == 'L' else 0,
        'Type_M':                  1 if machine_type == 'M' else 0,
        'Air temperature [K]':     air_temp,
        'Process temperature [K]': proc_temp,
    }])


def _get_severity(prob_pct):
    if prob_pct < 20:  return 'Healthy'
    if prob_pct < 50:  return 'Warning'
    if prob_pct < 80:  return 'High Risk'
    return 'Critical'


def predict(air_temp, proc_temp, rpm, torque, tool_wear, machine_type='M') -> dict:
    """
    Run unified prediction and return all 7 enriched outputs.

    Parameters
    ----------
    air_temp      : float  Air temperature (K)
    proc_temp     : float  Process temperature (K)
    rpm           : float  Rotational speed (rpm)
    torque        : float  Torque (Nm)
    tool_wear     : float  Tool wear (minutes)
    machine_type  : str    'L', 'M', or 'H'

    Returns
    -------
    dict with keys:
        machine_failure, failure_probability, failure_type,
        failure_type_confidence, recommendations,
        machine_health_score, severity_level,
        maintenance_priority, components_to_inspect,
        maintenance_window, operator_action, machine_status
    """
    _load()
    b        = _BUNDLE
    FEATURES = b['features']

    row  = _build_row(air_temp, proc_temp, rpm, torque, tool_wear, machine_type)
    X    = row[FEATURES]

    # ── Model 1: Machine Failure ──────────────────────────────
    fail_pred  = b['failure_model'].predict(X)[0]
    fail_proba = b['failure_model'].predict_proba(X)[0]
    fail_prob  = float(fail_proba[1]) * 100      # % probability of failure

    # ── Model 2: Failure Type ─────────────────────────────────
    type_pred   = b['failure_type_model'].predict(X)[0]
    type_probas = dict(zip(
        b['failure_type_model'].classes_,
        b['failure_type_model'].predict_proba(X)[0]
    ))
    type_confidence = float(max(type_probas.values())) * 100

    # ── Severity (drives all other logic) ─────────────────────
    severity = _get_severity(fail_prob)

    # ── Health Score ──────────────────────────────────────────
    health_score = round(100 - fail_prob, 1)

    # ── Components to Inspect ─────────────────────────────────
    fail_type_key = type_pred if fail_pred else 'No Failure'
    components    = b['component_map'].get(fail_type_key,
                                           ['General Inspection'])

    # ── Recommendations string ────────────────────────────────
    comp_str = ', '.join(components)
    if fail_pred:
        recommendations = (
            f"Inspect: {comp_str}. "
            f"{b['action_map'][severity]}. "
            f"Maintenance {b['window_map'][severity]}."
        )
    else:
        recommendations = "No immediate action required. Continue standard monitoring."

    return {
        # ── Core Predictions ──────────────────────────────────
        'machine_failure':        'Yes' if fail_pred else 'No',
        'failure_probability':    f"{fail_prob:.1f}%",
        'failure_type':           type_pred,
        'failure_type_confidence': f"{type_confidence:.1f}%",
        'recommendations':        recommendations,

        # ── Enriched Outputs ─────────────────────────────────
        'machine_health_score':   f"{health_score}/100",
        'severity_level':         severity,
        'maintenance_priority':   b['priority_map'][severity],
        'components_to_inspect':  components,
        'maintenance_window':     b['window_map'][severity],
        'operator_action':        b['action_map'][severity],
        'machine_status':         b['status_map'][severity],

        # ── Raw Numbers (for UI charting) ─────────────────────
        '_health_score_raw':      health_score,
        '_failure_prob_raw':      round(fail_prob, 2),
        '_type_confidence_raw':   round(type_confidence, 2),
        '_type_probabilities':    {k: round(v*100, 1) for k, v in
                                   sorted(type_probas.items(), key=lambda x: -x[1])},
    }


def predict_batch(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Predict for a DataFrame with columns:
    air_temp, proc_temp, rpm, torque, tool_wear, machine_type
    """
    results = []
    for _, row in df_input.iterrows():
        r = predict(
            air_temp=row.get('air_temp', 298.0),
            proc_temp=row.get('proc_temp', 308.5),
            rpm=row.get('rpm', 1500),
            torque=row.get('torque', 40.0),
            tool_wear=row.get('tool_wear', 0),
            machine_type=row.get('machine_type', 'M'),
        )
        results.append(r)
    out = df_input.copy()
    for key in results[0]:
        if not key.startswith('_type_prob'):   # skip nested dict
            out[key] = [r[key] for r in results]
    return out


if __name__ == '__main__':
    print("=" * 65)
    print("  UNIFIED MODEL — 8 SCENARIO OUTPUT DEMO")
    print("=" * 65)

    test_cases = [
        dict(air_temp=298.1, proc_temp=308.6, rpm=1551,  torque=42.8, tool_wear=0,   machine_type='M', name='Brand new tool'),
        dict(air_temp=298.5, proc_temp=309.0, rpm=1500,  torque=45.0, tool_wear=80,  machine_type='L', name='Mid-life, normal'),
        dict(air_temp=298.8, proc_temp=309.2, rpm=1400,  torque=60.0, tool_wear=150, machine_type='L', name='High torque, worn'),
        dict(air_temp=298.9, proc_temp=309.1, rpm=2861,  torque=4.6,  tool_wear=143, machine_type='L', name='High RPM spike (real failure)'),
        dict(air_temp=298.9, proc_temp=309.0, rpm=1410,  torque=65.7, tool_wear=191, machine_type='L', name='High torque + near end of life'),
        dict(air_temp=297.5, proc_temp=308.5, rpm=2564,  torque=12.8, tool_wear=127, machine_type='L', name='RPM anomaly (real failure)'),
        dict(air_temp=298.0, proc_temp=308.2, rpm=1282,  torque=60.7, tool_wear=216, machine_type='L', name='Overloaded + fully worn'),
        dict(air_temp=300.0, proc_temp=313.0, rpm=1500,  torque=45.0, tool_wear=50,  machine_type='H', name='High heat dissipation'),
    ]

    STATUS_ICON = {
        'Healthy': '[OK]     ', 'Warning': '[WARN]   ',
        'High Risk': '[HIGH]   ', 'Critical': '[CRITICAL]'
    }

    for tc in test_cases:
        name = tc.pop('name')
        res  = predict(**tc)

        icon = STATUS_ICON.get(res['severity_level'], '⚪')
        print(f"\n  {icon} {name}")
        print(f"  {'─'*60}")
        print(f"  Machine Failure        : {res['machine_failure']}")
        print(f"  Failure Probability    : {res['failure_probability']}")
        print(f"  Machine Health Score   : {res['machine_health_score']}")
        print(f"  Severity Level         : {res['severity_level']}")
        print(f"  Machine Status         : {res['machine_status']}")
        print(f"  Failure Type           : {res['failure_type']}  (conf: {res['failure_type_confidence']})")
        print(f"  Components to Inspect  : {', '.join(res['components_to_inspect'])}")
        print(f"  Maintenance Priority   : {res['maintenance_priority']}")
        print(f"  Maintenance Window     : {res['maintenance_window']}")
        print(f"  Operator Action        : {res['operator_action']}")
        print(f"  Recommendation         : {res['recommendations']}")
        print(f"  Type Probabilities     : {res['_type_probabilities']}")
