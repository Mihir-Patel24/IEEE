"""
database/db_client.py
Dual-mode database client.
 • Supabase PostgreSQL when SUPABASE_URL env var is set (cloud deploy)
 • SQLite otherwise (local / demo)

All public methods return plain Python dicts — no ORM coupling.
"""
from __future__ import annotations
import os, sys, sqlite3, hashlib, json, uuid
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

# ── Supabase client (optional) ────────────────────────────────────
_supabase = None
if settings.is_supabase_configured:
    try:
        from supabase import create_client
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    except ImportError:
        pass  # supabase-py not installed — fall back to SQLite


# ─────────────────────────────────────────────────────────────────
#  SQLite helpers
# ─────────────────────────────────────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_sqlite() -> None:
    """Create tables if they do not exist."""
    conn = _get_conn()
    cur  = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            full_name   TEXT NOT NULL,
            company     TEXT DEFAULT '',
            factory     TEXT DEFAULT '',
            department  TEXT DEFAULT '',
            role        TEXT DEFAULT 'Maintenance Engineer',
            password_hash TEXT NOT NULL,
            avatar_color  TEXT DEFAULT '#1e40af',
            created_at  TEXT NOT NULL,
            last_login  TEXT
        );

        CREATE TABLE IF NOT EXISTS machines (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            machine_id   TEXT NOT NULL,
            machine_name TEXT NOT NULL,
            machine_type TEXT DEFAULT 'CNC Milling',
            material     TEXT DEFAULT '',
            factory      TEXT DEFAULT '',
            location     TEXT DEFAULT '',
            status       TEXT DEFAULT 'Active',
            created_at   TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            machine_id      TEXT DEFAULT 'CNC-00',
            tool_health     REAL DEFAULT 0,
            machine_health  REAL DEFAULT 0,
            tool_wear       REAL DEFAULT 0,
            remaining_rul   REAL DEFAULT 0,
            failure_risk    REAL DEFAULT 0,
            failure_prob    REAL DEFAULT 0,
            failure_type    TEXT DEFAULT '',
            machine_status  TEXT DEFAULT '',
            maintenance_priority TEXT DEFAULT '',
            overall_risk    REAL DEFAULT 0,
            source          TEXT DEFAULT 'local',
            payload_json    TEXT DEFAULT '{}',
            result_json     TEXT DEFAULT '{}',
            created_at      TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            machine_id  TEXT DEFAULT '',
            title       TEXT NOT NULL,
            detail      TEXT DEFAULT '',
            level       TEXT DEFAULT 'info',
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_history (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            machine_id  TEXT NOT NULL,
            task        TEXT NOT NULL,
            priority    TEXT DEFAULT 'Medium',
            status      TEXT DEFAULT 'Pending',
            technician  TEXT DEFAULT '',
            est_time    TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            scheduled_at TEXT,
            completed_at TEXT,
            created_at   TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            action     TEXT NOT NULL,
            detail     TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            email      TEXT NOT NULL,
            token      TEXT UNIQUE NOT NULL,
            used       INTEGER DEFAULT 0,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str) -> str:
    salt = settings.secret_key
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────
#  DatabaseClient
# ─────────────────────────────────────────────────────────────────
class DatabaseClient:
    """Unified DB client — SQLite locally, Supabase in cloud."""

    def __init__(self):
        if not settings.is_supabase_configured:
            _init_sqlite()

    # ── Users ─────────────────────────────────────────────────────

    def create_user(self, email: str, password: str, full_name: str,
                    company: str = "", factory: str = "",
                    department: str = "", role: str = "Maintenance Engineer") -> dict:
        uid = str(uuid.uuid4())
        pw_hash = _hash_password(password)
        import random
        colors = ["#1e40af","#059669","#7c3aed","#0891b2","#dc2626","#d97706"]
        avatar_color = random.choice(colors)
        now = _now()

        if _supabase:
            data = {
                "id": uid, "email": email, "full_name": full_name,
                "company": company, "factory": factory,
                "department": department, "role": role,
                "password_hash": pw_hash, "avatar_color": avatar_color,
                "created_at": now,
            }
            res = _supabase.table("users").insert(data).execute()
            return res.data[0] if res.data else {}

        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO users
                   (id,email,full_name,company,factory,department,role,
                    password_hash,avatar_color,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (uid, email, full_name, company, factory, department, role,
                 pw_hash, avatar_color, now)
            )
            conn.commit()
            return self.get_user_by_email(email) or {}
        except sqlite3.IntegrityError:
            raise ValueError("Email already registered.")
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> dict | None:
        if _supabase:
            res = _supabase.table("users").select("*").eq("email", email).execute()
            return res.data[0] if res.data else None
        conn = _get_conn()
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return _row_to_dict(row)

    def get_user_by_id(self, uid: str) -> dict | None:
        if _supabase:
            res = _supabase.table("users").select("*").eq("id", uid).execute()
            return res.data[0] if res.data else None
        conn = _get_conn()
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        conn.close()
        return _row_to_dict(row)

    def verify_password(self, email: str, password: str) -> dict | None:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if user.get("password_hash") != _hash_password(password):
            return None
        # Update last login
        self._update_last_login(user["id"])
        return user

    def _update_last_login(self, uid: str) -> None:
        now = _now()
        if _supabase:
            _supabase.table("users").update({"last_login": now}).eq("id", uid).execute()
            return
        conn = _get_conn()
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now, uid))
        conn.commit()
        conn.close()

    def update_user_profile(self, uid: str, **kwargs: Any) -> None:
        allowed = {"full_name","company","factory","department","role"}
        data = {k: v for k, v in kwargs.items() if k in allowed}
        if not data:
            return
        if _supabase:
            _supabase.table("users").update(data).eq("id", uid).execute()
            return
        conn = _get_conn()
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*data.values(), uid))
        conn.commit()
        conn.close()

    # ── Predictions ───────────────────────────────────────────────

    def save_prediction(self, user_id: str, machine_id: str,
                        result: dict, payload: dict) -> str:
        pid = str(uuid.uuid4())
        now = _now()
        tool = result.get("tool_prediction") or {}
        maint = result.get("maintenance_prediction") or {}
        decision = result.get("decision") or {}

        row = {
            "id": pid, "user_id": user_id, "machine_id": machine_id,
            "tool_health":   float(tool.get("tool_health", result.get("tool_health", 0)) or 0),
            "machine_health": float(maint.get("machine_health", result.get("machine_health", 0)) or 0),
            "tool_wear":     float(tool.get("tool_wear", result.get("vb", 0)) or 0),
            "remaining_rul": float(tool.get("remaining_useful_life", result.get("rul", 0)) or 0),
            "failure_risk":  float(result.get("failure_risk", decision.get("overall_risk", 0)) or 0),
            "failure_prob":  float(maint.get("failure_probability", result.get("failure_probability", 0)) or 0),
            "failure_type":  maint.get("failure_type", result.get("failure_type", "")),
            "machine_status": result.get("machine_status", decision.get("overall_status", "")),
            "maintenance_priority": decision.get("maintenance_priority", result.get("maintenance_priority", "")),
            "overall_risk":  float(decision.get("overall_risk", result.get("failure_risk", 0)) or 0),
            "source": result.get("source", "local"),
            "payload_json": json.dumps(payload),
            "result_json":  json.dumps(result),
            "created_at": now,
        }

        if _supabase:
            _supabase.table("predictions").insert(row).execute()
            return pid

        conn = _get_conn()
        cols = ", ".join(row.keys())
        placeholders = ", ".join("?" * len(row))
        conn.execute(f"INSERT INTO predictions ({cols}) VALUES ({placeholders})",
                     list(row.values()))
        conn.commit()
        conn.close()
        return pid

    def get_user_predictions(self, user_id: str, limit: int = 100) -> list[dict]:
        if _supabase:
            res = (_supabase.table("predictions")
                   .select("*").eq("user_id", user_id)
                   .order("created_at", desc=True).limit(limit).execute())
            return res.data or []

        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
        return _rows_to_list(rows)

    def get_prediction_count(self, user_id: str) -> int:
        if _supabase:
            res = _supabase.table("predictions").select("id", count="exact").eq("user_id", user_id).execute()
            return res.count or 0
        conn = _get_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        conn.close()
        return count

    # ── Machines ──────────────────────────────────────────────────

    def register_machine(self, user_id: str, machine_id: str, machine_name: str,
                         machine_type: str = "CNC Milling", material: str = "",
                         factory: str = "", location: str = "") -> dict:
        mid = str(uuid.uuid4())
        now = _now()
        row = {
            "id": mid, "user_id": user_id,
            "machine_id": machine_id, "machine_name": machine_name,
            "machine_type": machine_type, "material": material,
            "factory": factory, "location": location,
            "status": "Active", "created_at": now,
        }
        if _supabase:
            res = _supabase.table("machines").insert(row).execute()
            return res.data[0] if res.data else {}
        conn = _get_conn()
        conn.execute(
            """INSERT INTO machines
               (id,user_id,machine_id,machine_name,machine_type,material,
                factory,location,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (mid, user_id, machine_id, machine_name, machine_type,
             material, factory, location, "Active", now)
        )
        conn.commit()
        conn.close()
        return self.get_user_machines(user_id)[0] if self.get_user_machines(user_id) else {}

    def get_user_machines(self, user_id: str) -> list[dict]:
        if _supabase:
            res = _supabase.table("machines").select("*").eq("user_id", user_id).execute()
            return res.data or []
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM machines WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return _rows_to_list(rows)

    def update_machine_status(self, machine_id: str, status: str) -> None:
        """Update the status field of a machine record by machine_id."""
        if _supabase:
            _supabase.table("machines").update({"status": status}).eq("machine_id", machine_id).execute()
            return
        conn = _get_conn()
        conn.execute("UPDATE machines SET status=? WHERE machine_id=?", (status, machine_id))
        conn.commit()
        conn.close()

    def update_machine(self, record_id: str, **kwargs: Any) -> None:
        """Update editable fields of a machine by its primary key (id)."""
        allowed = {"machine_name", "machine_type", "material", "factory", "location", "status"}
        data = {k: v for k, v in kwargs.items() if k in allowed}
        if not data:
            return
        if _supabase:
            _supabase.table("machines").update(data).eq("id", record_id).execute()
            return
        conn = _get_conn()
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE machines SET {sets} WHERE id=?", (*data.values(), record_id))
        conn.commit()
        conn.close()

    def delete_machine(self, record_id: str) -> None:
        """Delete a machine record by its primary key (id)."""
        if _supabase:
            _supabase.table("machines").delete().eq("id", record_id).execute()
            return
        conn = _get_conn()
        conn.execute("DELETE FROM machines WHERE id=?", (record_id,))
        conn.commit()
        conn.close()

    # ── Alerts ────────────────────────────────────────────────────

    def save_alert(self, user_id: str, title: str, detail: str,
                   level: str = "info", machine_id: str = "") -> None:
        row = {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "machine_id": machine_id, "title": title,
            "detail": detail, "level": level,
            "is_read": 0, "created_at": _now(),
        }
        if _supabase:
            _supabase.table("alerts").insert(row).execute()
            return
        conn = _get_conn()
        conn.execute(
            """INSERT INTO alerts
               (id,user_id,machine_id,title,detail,level,is_read,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            list(row.values())
        )
        conn.commit()
        conn.close()

    def get_user_alerts(self, user_id: str, limit: int = 20) -> list[dict]:
        if _supabase:
            res = (_supabase.table("alerts").select("*").eq("user_id", user_id)
                   .order("created_at", desc=True).limit(limit).execute())
            return res.data or []
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM alerts WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
        return _rows_to_list(rows)

    def get_alert_counts(self, user_id: str) -> dict:
        """Return {total, unread, critical, warning, info} counts for a user."""
        alerts = self.get_user_alerts(user_id, limit=200)
        return {
            "total":    len(alerts),
            "unread":   sum(1 for a in alerts if not a.get("is_read")),
            "critical": sum(1 for a in alerts if a.get("level") == "critical"),
            "warning":  sum(1 for a in alerts if a.get("level") == "warning"),
            "info":     sum(1 for a in alerts if a.get("level") == "info"),
        }

    def mark_alerts_read(self, user_id: str) -> None:
        """Mark all alerts for a user as read."""
        if _supabase:
            _supabase.table("alerts").update({"is_read": 1}).eq("user_id", user_id).execute()
            return
        conn = _get_conn()
        conn.execute("UPDATE alerts SET is_read=1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

    def mark_alert_read(self, alert_id: str) -> None:
        """Mark a single alert as read by its primary key."""
        if _supabase:
            _supabase.table("alerts").update({"is_read": True}).eq("id", alert_id).execute()
            return
        conn = _get_conn()
        conn.execute("UPDATE alerts SET is_read=1 WHERE id=?", (alert_id,))
        conn.commit()
        conn.close()

    def get_db_stats(self, user_id: str) -> dict:
        """Return row counts for dashboard DB health indicator."""
        return {
            "predictions":  self.get_prediction_count(user_id),
            "machines":     len(self.get_user_machines(user_id)),
            "alerts":       self.get_alert_counts(user_id)["total"],
            "db_mode":      "Supabase" if _supabase else "SQLite",
        }

    def log_audit(self, user_id: str, action: str, detail: str = "") -> None:
        row = {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "action": action, "detail": detail,
            "ip_address": "", "created_at": _now(),
        }
        if _supabase:
            _supabase.table("audit_logs").insert(row).execute()
            return
        conn = _get_conn()
        conn.execute(
            "INSERT INTO audit_logs (id,user_id,action,detail,ip_address,created_at) VALUES (?,?,?,?,?,?)",
            list(row.values())
        )
        conn.commit()
        conn.close()

    # ── Password Reset Tokens ─────────────────────────────────────

    def create_password_reset_token(self, email: str) -> str | None:
        """
        Generate a secure reset token for *email*.
        Returns the token string (shown in demo mode), or None if email not found.
        Tokens expire after settings.password_reset_token_expiry_hours (default 1h).
        """
        import secrets
        from datetime import timedelta

        user = self.get_user_by_email(email)
        if not user:
            return None

        token      = secrets.token_urlsafe(32)
        uid        = user["id"]
        now        = _now()
        expiry_hrs = getattr(settings, "password_reset_token_expiry_hours", 1)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=expiry_hrs)
        ).isoformat()

        row = {
            "id":         str(uuid.uuid4()),
            "user_id":    uid,
            "email":      email,
            "token":      token,
            "used":       0,
            "expires_at": expires_at,
            "created_at": now,
        }

        if _supabase:
            _supabase.table("password_reset_tokens").insert(row).execute()
        else:
            conn = _get_conn()
            conn.execute(
                """INSERT INTO password_reset_tokens
                   (id,user_id,email,token,used,expires_at,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                [row["id"], row["user_id"], row["email"], row["token"],
                 row["used"], row["expires_at"], row["created_at"]],
            )
            conn.commit()
            conn.close()

        self.log_audit(uid, "password_reset_request", f"Reset token created for {email}")
        return token

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Validate *token* and update the user's password.
        Returns True on success, False on invalid/expired/used token.
        """
        now = datetime.now(timezone.utc).isoformat()

        if _supabase:
            res = (
                _supabase.table("password_reset_tokens")
                .select("*").eq("token", token).eq("used", 0).execute()
            )
            rows = res.data or []
        else:
            conn = _get_conn()
            rows = _rows_to_list(
                conn.execute(
                    "SELECT * FROM password_reset_tokens WHERE token=? AND used=0",
                    (token,)
                ).fetchall()
            )
            conn.close()

        if not rows:
            return False

        rec = rows[0]
        if rec["expires_at"] < now:
            return False   # expired

        uid       = rec["user_id"]
        new_hash  = _hash_password(new_password)

        # Update password
        if _supabase:
            _supabase.table("users").update({"password_hash": new_hash}).eq("id", uid).execute()
            _supabase.table("password_reset_tokens").update({"used": 1}).eq("token", token).execute()
        else:
            conn = _get_conn()
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, uid))
            conn.execute("UPDATE password_reset_tokens SET used=1 WHERE token=?", (token,))
            conn.commit()
            conn.close()

        self.log_audit(uid, "password_reset_complete", "Password updated via reset token")
        return True


db = DatabaseClient()
