"""
auth/rbac.py — Role-Based Access Control (RBAC)
================================================
Defines roles, permissions, and guard functions.

Roles (hierarchy, highest → lowest):
  Admin > Plant Manager > Maintenance Engineer > Operator

Usage:
    from auth.rbac import require_role, has_permission, ROLE_PERMISSIONS

    # In a view:
    if not require_role("Plant Manager"):
        st.stop()

    # Check a specific capability:
    if has_permission("view_cost_analysis"):
        render_cost_section()
"""
from __future__ import annotations
import streamlit as st

# ── Role hierarchy ────────────────────────────────────────────────
ROLES: list[str] = [
    "Admin",
    "Plant Manager",
    "Maintenance Engineer",
    "Operator",
]

# ── Permission matrix ─────────────────────────────────────────────
# key: permission name  →  value: set of roles that have it
ROLE_PERMISSIONS: dict[str, set[str]] = {
    # Dashboard
    "view_dashboard":        {"Admin", "Plant Manager", "Maintenance Engineer", "Operator"},
    # Predictions
    "run_prediction":        {"Admin", "Plant Manager", "Maintenance Engineer"},
    "view_predictions":      {"Admin", "Plant Manager", "Maintenance Engineer"},
    # Machine Health
    "view_machine_health":   {"Admin", "Plant Manager", "Maintenance Engineer", "Operator"},
    # Maintenance
    "view_maintenance":      {"Admin", "Plant Manager", "Maintenance Engineer", "Operator"},
    "edit_maintenance":      {"Admin", "Plant Manager", "Maintenance Engineer"},
    "approve_maintenance":   {"Admin", "Plant Manager"},
    # Reports
    "view_reports":          {"Admin", "Plant Manager", "Maintenance Engineer"},
    "export_reports":        {"Admin", "Plant Manager"},
    # Cost Analysis
    "view_cost_analysis":    {"Admin", "Plant Manager"},
    # Settings
    "view_settings":         {"Admin", "Plant Manager", "Maintenance Engineer", "Operator"},
    "edit_settings":         {"Admin", "Plant Manager"},
    # Admin panel
    "view_admin":            {"Admin"},
    "manage_users":          {"Admin"},
    # Machine registry
    "register_machine":      {"Admin", "Plant Manager", "Maintenance Engineer"},
    "delete_machine":        {"Admin", "Plant Manager"},
}

# ── Role display metadata ─────────────────────────────────────────
ROLE_META: dict[str, dict] = {
    "Admin": {
        "color":  "#DC2626",
        "bg":     "#FEF2F2",
        "border": "#FECACA",
        "icon":   "🛡️",
        "desc":   "Full system access. Manage users, settings, all data.",
    },
    "Plant Manager": {
        "color":  "#7C3AED",
        "bg":     "#F5F3FF",
        "border": "#DDD6FE",
        "icon":   "🏭",
        "desc":   "Oversee operations, approve maintenance, export reports.",
    },
    "Maintenance Engineer": {
        "color":  "#2563EB",
        "bg":     "#EFF6FF",
        "border": "#BFDBFE",
        "icon":   "🔧",
        "desc":   "Run predictions, manage maintenance tasks, view reports.",
    },
    "Operator": {
        "color":  "#16A34A",
        "bg":     "#F0FDF4",
        "border": "#BBF7D0",
        "icon":   "👷",
        "desc":   "Monitor dashboard and machine health. Read-only access.",
    },
}


def _current_role() -> str:
    """Return the authenticated user's role from session state."""
    from auth.auth_service import auth          # local import to avoid circular
    return auth.current_user().get("role", "Operator")


def has_permission(permission: str) -> bool:
    """Return True if the current user's role grants *permission*."""
    role = _current_role()
    allowed = ROLE_PERMISSIONS.get(permission, set())
    return role in allowed


def require_role(minimum_role: str) -> bool:
    """
    Return True if the current user meets or exceeds *minimum_role*.
    Call ``st.stop()`` yourself if you want to halt rendering.

    Example::

        if not require_role("Plant Manager"):
            st.error("Access restricted to Plant Manager and above.")
            st.stop()
    """
    role = _current_role()
    if role not in ROLES:
        return False
    return ROLES.index(role) <= ROLES.index(minimum_role)


def role_badge_html(role: str) -> str:
    """Return an HTML badge string for the given role."""
    meta = ROLE_META.get(role, ROLE_META["Operator"])
    return (
        f'<span style="background:{meta["bg"]};color:{meta["color"]};'
        f'border:1px solid {meta["border"]};border-radius:20px;'
        f'font-size:11px;font-weight:600;padding:3px 10px;white-space:nowrap">'
        f'{meta["icon"]} {role}</span>'
    )
