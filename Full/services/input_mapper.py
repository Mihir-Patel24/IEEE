from __future__ import annotations

from typing import Any


class InputMappingError(ValueError):
    pass


class InputMapper:
    """Convert dashboard payloads into model-ready inputs."""

    TOOL_WEAR_FIELDS = [
        "smcAC_mean",
        "smcAC_rms",
        "smcAC_std",
        "smcDC_mean",
        "smcDC_rms",
        "smcDC_std",
        "vib_table_mean",
        "vib_table_rms",
        "vib_spindle_mean",
        "vib_spindle_rms",
        "AE_table_mean",
        "AE_table_rms",
        "AE_spindle_mean",
        "AE_spindle_rms",
        "time",
        "DOC",
        "feed",
        "material",
        "VB_lag1",
        "VB_lag2",
        "run_norm",
    ]

    AI4I_FIELDS = [
        "air_temp",
        "proc_temp",
        "rpm",
        "torque",
        "tool_wear",
        "machine_type",
    ]

    def validate_tool_wear_payload(self, payload: dict[str, Any]) -> None:
        missing = [field for field in self.TOOL_WEAR_FIELDS if field not in payload]
        if missing:
            raise InputMappingError(
                f"Missing tool wear payload fields: {', '.join(missing)}"
            )

    def validate_ai4i_payload(self, payload: dict[str, Any]) -> None:
        missing = [field for field in self.AI4I_FIELDS if field not in payload]
        if missing:
            raise InputMappingError(
                f"Missing AI4I payload fields: {', '.join(missing)}"
            )

    def map_to_tool_wear(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.validate_tool_wear_payload(payload)
        return {field: payload[field] for field in self.TOOL_WEAR_FIELDS}

    def map_to_ai4i(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.validate_ai4i_payload(payload)
        return {field: payload[field] for field in self.AI4I_FIELDS}
