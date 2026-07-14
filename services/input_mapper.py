from __future__ import annotations

import math
from typing import Any


class InputMappingError(ValueError):
    pass


class InputMapper:
    """Convert dashboard payloads into model-ready inputs."""

    TOOL_WEAR_FIELDS = [
        "smcAC_mean", "smcAC_rms", "smcAC_std",
        "smcDC_mean", "smcDC_rms", "smcDC_std",
        "vib_table_mean", "vib_table_rms",
        "vib_spindle_mean", "vib_spindle_rms",
        "AE_table_mean", "AE_table_rms",
        "AE_spindle_mean", "AE_spindle_rms",
        "time", "DOC", "feed", "material",
        "VB_lag1", "VB_lag2", "run_norm",
    ]

    AI4I_FIELDS = [
        "air_temp", "proc_temp", "rpm", "torque",
        "tool_wear", "machine_type",
    ]

    # ── Operator-level field defaults ─────────────────────────────
    _MATERIAL_ENC = {"cast iron": 1, "steel": 2, "aluminum": 3, "titanium": 4}
    _MACHINE_TYPE_ENC = {"m": "M", "l": "L", "h": "H"}

    def validate_tool_wear_payload(self, payload: dict[str, Any]) -> None:
        missing = [f for f in self.TOOL_WEAR_FIELDS if f not in payload]
        if missing:
            raise InputMappingError(f"Missing tool wear fields: {', '.join(missing)}")

    def validate_ai4i_payload(self, payload: dict[str, Any]) -> None:
        missing = [f for f in self.AI4I_FIELDS if f not in payload]
        if missing:
            raise InputMappingError(f"Missing AI4I fields: {', '.join(missing)}")

    def map_to_tool_wear(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.validate_tool_wear_payload(payload)
        return {f: payload[f] for f in self.TOOL_WEAR_FIELDS}

    def map_to_ai4i(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.validate_ai4i_payload(payload)
        return {f: payload[f] for f in self.AI4I_FIELDS}

    # ── Operator input → full ML payload ─────────────────────────
    def map_from_operator_input(self, op: dict[str, Any]) -> dict[str, Any]:
        """
        Accept manufacturing-level operator inputs and automatically derive
        all ML feature fields required by both models.

        Operator fields (all optional with sensible defaults):
            machine_id, material, machine_type, operation_type,
            cutting_speed, feed_rate, depth_of_cut, spindle_rpm,
            torque, air_temperature, process_temperature,
            tool_diameter, coolant, batch_number, operator_name,
            machining_time, workpiece_material
        """
        # ── Parse operator inputs ─────────────────────────────────
        material_str = str(op.get("material", "cast iron")).lower().strip()
        material_enc = self._MATERIAL_ENC.get(material_str, 1)

        machine_type_raw = str(op.get("machine_type", "M")).strip()
        machine_type = self._MACHINE_TYPE_ENC.get(machine_type_raw.lower(), machine_type_raw.upper())

        feed        = float(op.get("feed_rate", 0.5))
        doc         = float(op.get("depth_of_cut", 0.75))
        rpm         = float(op.get("spindle_rpm", 1500))
        torque      = float(op.get("torque", 40.0))
        air_temp    = float(op.get("air_temperature", 298.1))
        proc_temp   = float(op.get("process_temperature", 308.6))
        time_val    = float(op.get("machining_time", 10.0))
        tool_diam   = float(op.get("tool_diameter", 10.0))
        cutting_spd = float(op.get("cutting_speed", rpm * math.pi * tool_diam / 1000))

        # ── Derived / engineered features ─────────────────────────
        # Power proxy: torque × angular velocity
        omega = rpm * 2 * math.pi / 60
        power = torque * omega  # Watts

        # Heat index: temperature difference
        temp_diff = proc_temp - air_temp

        # Torque-wear proxy (normalised)
        torque_wear = torque * time_val / 1000.0

        # Normalised run position (0–1 over a 50-min run)
        run_norm = min(time_val / 50.0, 1.0)

        # Sensor signal estimates from machining parameters
        # smcAC: AC spindle current — scales with cutting load
        load_factor = (doc * feed * cutting_spd) / 100.0
        smcAC_mean  = -0.165 + load_factor * 0.05
        smcAC_std   = 0.08 + load_factor * 0.02
        smcAC_rms   = abs(smcAC_mean) * 1.05 + smcAC_std

        # smcDC: DC spindle current — scales with torque
        smcDC_mean = 4.0 + (torque / 80.0) * 6.0
        smcDC_std  = 0.06 + (torque / 80.0) * 0.04
        smcDC_rms  = smcDC_mean * 1.01

        # Vibration — scales with rpm and depth of cut
        vib_base        = 0.5 + (rpm / 3000.0) * 1.0 + doc * 0.3
        vib_table_mean  = vib_base * 0.9
        vib_table_rms   = vib_table_mean * 1.02
        vib_spindle_mean = vib_base * 0.45
        vib_spindle_rms  = vib_spindle_mean * 1.02

        # Acoustic emission — scales with cutting speed and doc
        ae_base        = 0.1 + (cutting_spd / 500.0) * 0.3 + doc * 0.05
        AE_table_mean  = ae_base * 0.85
        AE_table_rms   = AE_table_mean * 1.02
        AE_spindle_mean = ae_base * 1.1
        AE_spindle_rms  = AE_spindle_mean * 1.02

        # VB lag features — use session history if available, else 0
        VB_lag1 = float(op.get("vb_lag1", 0.0))
        VB_lag2 = float(op.get("vb_lag2", 0.0))

        # Tool wear (AI4I field) — cumulative minutes on tool
        tool_wear_min = float(op.get("tool_wear_minutes", time_val))

        return {
            # Tool wear model fields
            "smcAC_mean": round(smcAC_mean, 4),
            "smcAC_rms":  round(smcAC_rms, 4),
            "smcAC_std":  round(smcAC_std, 4),
            "smcDC_mean": round(smcDC_mean, 4),
            "smcDC_rms":  round(smcDC_rms, 4),
            "smcDC_std":  round(smcDC_std, 4),
            "vib_table_mean":   round(vib_table_mean, 4),
            "vib_table_rms":    round(vib_table_rms, 4),
            "vib_spindle_mean": round(vib_spindle_mean, 4),
            "vib_spindle_rms":  round(vib_spindle_rms, 4),
            "AE_table_mean":    round(AE_table_mean, 4),
            "AE_table_rms":     round(AE_table_rms, 4),
            "AE_spindle_mean":  round(AE_spindle_mean, 4),
            "AE_spindle_rms":   round(AE_spindle_rms, 4),
            "time":     round(time_val, 2),
            "DOC":      round(doc, 3),
            "feed":     round(feed, 3),
            "material": material_enc,
            "VB_lag1":  round(VB_lag1, 4),
            "VB_lag2":  round(VB_lag2, 4),
            "run_norm": round(run_norm, 4),
            # AI4I model fields
            "air_temp":    round(air_temp, 2),
            "proc_temp":   round(proc_temp, 2),
            "rpm":         int(rpm),
            "torque":      round(torque, 2),
            "tool_wear":   round(tool_wear_min, 2),
            "machine_type": machine_type,
            # Metadata (not sent to models, used for display)
            "_derived": {
                "power_w":    round(power, 1),
                "temp_diff":  round(temp_diff, 2),
                "torque_wear": round(torque_wear, 4),
                "cutting_speed": round(cutting_spd, 2),
            },
        }
