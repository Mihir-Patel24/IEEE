"""
auth/auth_service.py — Session-based authentication
Works with SQLite locally and Supabase in cloud.
All state is stored in st.session_state.
"""
from __future__ import annotations
import os, sys, time
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from database.db_client import db


class AuthService:
    """Handles login, register, logout, and session management."""

    DEMO_USER = {
        "id":          "demo-user-0000",
        "email":       settings.demo_email,
        "full_name":   settings.demo_name,
        "company":     settings.demo_company,
        "factory":     settings.demo_factory,
        "department":  "Maintenance",
        "role":        settings.demo_role,
        "avatar_color": "#1e40af",
        "created_at":  "2024-01-01T00:00:00Z",
        "last_login":  None,
    }

    # ── Session keys ───────────────────────────────────────────────
    _KEY_AUTHENTICATED = "auth_authenticated"
    _KEY_USER         = "auth_user"
    _KEY_ERROR        = "auth_error"

    def is_authenticated(self) -> bool:
        return bool(st.session_state.get(self._KEY_AUTHENTICATED, False))

    def current_user(self) -> dict:
        return st.session_state.get(self._KEY_USER) or {}

    def user_id(self) -> str:
        return self.current_user().get("id", "")

    def user_name(self) -> str:
        u = self.current_user()
        return u.get("full_name", u.get("email", "User"))

    def user_initials(self) -> str:
        name = self.user_name()
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper() if name else "??"

    def login(self, email: str, password: str) -> bool:
        """Returns True on success, sets auth_error on failure."""
        st.session_state[self._KEY_ERROR] = ""

        # Demo mode bypass
        if settings.demo_mode and email == settings.demo_email and password == settings.demo_password:
            st.session_state[self._KEY_AUTHENTICATED] = True
            st.session_state[self._KEY_USER] = self.DEMO_USER
            return True

        try:
            user = db.verify_password(email, password)
            if user:
                st.session_state[self._KEY_AUTHENTICATED] = True
                st.session_state[self._KEY_USER] = user
                db.log_audit(user["id"], "login", f"Login from email: {email}")
                return True
            else:
                st.session_state[self._KEY_ERROR] = "Invalid email or password."
                return False
        except Exception as e:
            st.session_state[self._KEY_ERROR] = f"Login failed: {str(e)}"
            return False

    def register(self, email: str, password: str, full_name: str,
                 company: str = "", factory: str = "",
                 department: str = "", role: str = "Maintenance Engineer") -> bool:
        st.session_state[self._KEY_ERROR] = ""
        if len(password) < 6:
            st.session_state[self._KEY_ERROR] = "Password must be at least 6 characters."
            return False
        if not email or "@" not in email:
            st.session_state[self._KEY_ERROR] = "Please enter a valid email address."
            return False
        if not full_name.strip():
            st.session_state[self._KEY_ERROR] = "Full name is required."
            return False
        try:
            user = db.create_user(
                email=email, password=password, full_name=full_name,
                company=company, factory=factory,
                department=department, role=role,
            )
            if user:
                st.session_state[self._KEY_AUTHENTICATED] = True
                st.session_state[self._KEY_USER] = user
                db.log_audit(user.get("id",""), "register", f"New user: {email}")
                return True
            st.session_state[self._KEY_ERROR] = "Registration failed. Please try again."
            return False
        except ValueError as e:
            st.session_state[self._KEY_ERROR] = str(e)
            return False
        except Exception as e:
            st.session_state[self._KEY_ERROR] = f"Registration error: {str(e)}"
            return False

    def logout(self) -> None:
        uid = self.user_id()
        if uid:
            try:
                db.log_audit(uid, "logout")
            except Exception:
                pass
        for key in [self._KEY_AUTHENTICATED, self._KEY_USER, self._KEY_ERROR]:
            st.session_state.pop(key, None)

    def get_auth_error(self) -> str:
        return st.session_state.get(self._KEY_ERROR, "")

    def require_auth(self) -> bool:
        """Returns True if user is authenticated; used as guard in app.py."""
        return self.is_authenticated()

    # ── Role & Permission helpers (delegate to rbac module) ────────

    def user_role(self) -> str:
        """Return the current user's role string."""
        return self.current_user().get("role", "Operator")

    def has_permission(self, permission: str) -> bool:
        """Delegate to rbac.has_permission — avoids circular imports in views."""
        try:
            from auth.rbac import has_permission
            return has_permission(permission)
        except Exception:
            return False

    def is_admin(self) -> bool:
        return self.user_role() == "Admin"

    def is_plant_manager_or_above(self) -> bool:
        return self.user_role() in {"Admin", "Plant Manager"}

    # ── Session timeout ────────────────────────────────────────────

    def touch_session(self) -> None:
        """Record current time as the last activity timestamp."""
        st.session_state["_session_last_active"] = time.time()

    def session_is_expired(self) -> bool:
        """Return True if the session has exceeded the configured timeout."""
        last = st.session_state.get("_session_last_active")
        if last is None:
            return False
        timeout_seconds = settings.session_timeout_hours * 3600
        return (time.time() - last) > timeout_seconds

    def enforce_session_timeout(self) -> None:
        """
        Call this at the top of every authenticated page.
        If the session has expired, log the user out and trigger a rerun.
        """
        if self.is_authenticated() and self.session_is_expired():
            uid = self.user_id()
            try:
                from database.db_client import db as _db
                _db.log_audit(uid, "session_timeout", "Auto-logout after inactivity")
            except Exception:
                pass
            self.logout()
            st.warning("⏱️ Your session has expired. Please sign in again.")
            st.rerun()
        else:
            self.touch_session()


auth = AuthService()
