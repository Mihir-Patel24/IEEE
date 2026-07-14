"""
config/settings.py — Application configuration
Reads from environment variables, falls back to safe defaults.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field

# ── Load .env if python-dotenv is available ───────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(
        os.path.dirname(__file__), "..", "..", ".env"
    ))
except ImportError:
    pass


@dataclass
class AppConfig:
    # ── App ────────────────────────────────────────────────────────
    app_name:     str = "IndustrialMaint AI"
    app_version:  str = "3.0.0"
    app_subtitle: str = "Hybrid AI Predictive Maintenance Platform"

    # ── Supabase (optional — falls back to SQLite when not set) ────
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))

    # ── Database (SQLite fallback) ─────────────────────────────────
    db_path: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(__file__), "..", "industrialmaint.db"
    ))

    # ── Security ───────────────────────────────────────────────────
    secret_key: str = field(default_factory=lambda: os.getenv(
        "SECRET_KEY", "industrialmaint-secret-key-change-in-production"
    ))
    session_timeout_hours: int = 24

    # ── Feature Flags ──────────────────────────────────────────────
    use_supabase:     bool = field(default_factory=lambda: bool(os.getenv("SUPABASE_URL")))
    enable_pdf:       bool = True
    enable_email:     bool = False  # requires SMTP config
    demo_mode:        bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() == "true")

    # ── Demo credentials (demo mode only) ─────────────────────────
    demo_email:    str = "demo@industrialmaint.ai"
    demo_password: str = "Demo@1234"
    demo_name:     str = "Demo Engineer"
    demo_company:  str = "IndustrialMaint AI"
    demo_factory:  str = "Demo Factory — VIT"
    demo_role:     str = "Maintenance Engineer"

    # ── Alert thresholds ──────────────────────────────────────────
    default_wear_threshold: float = 0.3
    default_risk_threshold: int   = 60
    default_rul_threshold:  int   = 10

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


settings = AppConfig()
