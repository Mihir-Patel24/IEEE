"""
views/machine_registry.py — Machine Registry
=============================================
Full CRUD UI for managing the user's machine fleet.
- Register new machines
- Edit machine name, type, material, factory, location, status
- Delete machines (with confirmation)
- Live status toggle: Active / Idle / Maintenance / Offline
"""
from __future__ import annotations
import streamlit as st
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components import section_title, spacer, status_badge
from auth.auth_service import auth
from database.db_client import db
from auth.rbac import has_permission

_MACHINE_TYPES = [
    "CNC Milling", "CNC Turning", "Grinding Machine", "Drilling Machine",
    "Boring Machine", "Lathe", "Milling Machine", "Gear Hobbing",
    "EDM Machine", "3D Printer", "Injection Moulding", "Press Machine",
]

_MATERIALS = [
    "Steel", "Stainless Steel", "Aluminium", "Titanium",
    "Cast Iron", "Copper", "Brass", "Plastic", "Composite", "Other",
]

_STATUSES = ["Active", "Idle", "Maintenance", "Offline"]

_STATUS_COLORS = {
    "Active":      ("#16A34A", "#F0FDF4", "#BBF7D0"),
    "Idle":        ("#2563EB", "#EFF6FF", "#BFDBFE"),
    "Maintenance": ("#D97706", "#FFFBEB", "#FDE68A"),
    "Offline":     ("#DC2626", "#FEF2F2", "#FECACA"),
}


def _status_dot(status: str) -> str:
    color = _STATUS_COLORS.get(status, ("#6B7280", "#F9FAFB", "#E5E7EB"))[0]
    return (
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'border-radius:50%;background:{color};margin-right:6px"></span>'
    )


def render() -> None:
    user = auth.current_user()
    if not user:
        st.warning("Session not found.")
        return

    uid = user.get("id", "")

    # ── Load machines ─────────────────────────────────────────────
    try:
        machines = db.get_user_machines(uid)
    except Exception:
        machines = []

    # ── Header counts ─────────────────────────────────────────────
    total    = len(machines)
    active   = sum(1 for m in machines if m.get("status") == "Active")
    maint    = sum(1 for m in machines if m.get("status") == "Maintenance")
    offline  = sum(1 for m in machines if m.get("status") == "Offline")

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Total Machines",  total,   "#2563EB"),
        (c2, "Active",          active,  "#16A34A"),
        (c3, "In Maintenance",  maint,   "#D97706"),
        (c4, "Offline",         offline, "#DC2626"),
    ]:
        col.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(16)

    # ── Register new machine form ─────────────────────────────────
    can_register = has_permission("register_machine")

    section_title("Register New Machine")
    with st.expander("+ Add Machine to Fleet", expanded=(total == 0)):
        if not can_register:
            st.markdown(
                '<div style="background:#FFF7ED;border:1px solid #FED7AA;'
                'border-radius:8px;padding:10px 14px;font-size:13px;color:#92400E">'
                'Your role does not permit registering new machines.</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.form("reg_machine_form", clear_on_submit=True):
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    new_mid  = st.text_input("Machine ID *", placeholder="CNC-01", key="rm_id")
                with r1c2:
                    new_name = st.text_input("Machine Name *", placeholder="Main Milling Station", key="rm_name")

                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    new_type = st.selectbox("Machine Type", _MACHINE_TYPES, key="rm_type")
                with r2c2:
                    new_mat  = st.selectbox("Material", _MATERIALS, key="rm_mat")

                r3c1, r3c2 = st.columns(2)
                with r3c1:
                    new_factory  = st.text_input("Factory / Site", placeholder="Plant A", key="rm_factory")
                with r3c2:
                    new_location = st.text_input("Location / Line", placeholder="Line 3, Bay 7", key="rm_loc")

                spacer(4)
                submitted = st.form_submit_button(
                    "Register Machine", type="primary", use_container_width=True
                )

            if submitted:
                if not new_mid.strip() or not new_name.strip():
                    st.error("Machine ID and Machine Name are required.")
                else:
                    try:
                        db.register_machine(
                            user_id=uid,
                            machine_id=new_mid.strip().upper(),
                            machine_name=new_name.strip(),
                            machine_type=new_type,
                            material=new_mat,
                            factory=new_factory.strip(),
                            location=new_location.strip(),
                        )
                        db.log_audit(uid, "machine_registered", f"Machine {new_mid.strip().upper()} added")
                        st.success(f"✅ Machine **{new_name.strip()}** registered successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

    spacer(14)

    # ── Machine fleet table ───────────────────────────────────────
    section_title("Fleet Registry")

    if not machines:
        st.markdown(
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-radius:12px;padding:40px;text-align:center;color:#94A3B8">'
            '<div style="font-size:32px;margin-bottom:8px">🏭</div>'
            '<div style="font-size:15px;font-weight:600;color:#64748B">'
            'No machines registered yet</div>'
            '<div style="font-size:13px;margin-top:4px">'
            'Use the form above to add your first machine.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Column headers
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1.2, 2, 1.4, 1.2, 1.2, 1.2, 1.6])
    for col, lbl in zip(
        [h1, h2, h3, h4, h5, h6, h7],
        ["Machine ID", "Name", "Type", "Material", "Factory", "Status", "Actions"],
    ):
        col.markdown(
            f'<div style="font-size:11px;font-weight:700;color:#6B7280;'
            f'text-transform:uppercase;letter-spacing:.06em;padding:6px 0;'
            f'border-bottom:1px solid #E2E8F0">{lbl}</div>',
            unsafe_allow_html=True,
        )

    spacer(4)

    can_delete = has_permission("delete_machine")

    for m in machines:
        mid   = m.get("machine_id", "—")
        mname = m.get("machine_name", "—")
        mtype = m.get("machine_type", "—")
        mat   = m.get("material", "—")
        fac   = m.get("factory", "—")
        status= m.get("status", "Active")
        rec_id= m.get("id", "")

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.2, 2, 1.4, 1.2, 1.2, 1.2, 1.6])

        col1.markdown(
            f'<div style="font-size:13px;font-weight:700;color:#0F172A;padding:10px 0">{mid}</div>',
            unsafe_allow_html=True,
        )
        col2.markdown(
            f'<div style="font-size:13px;color:#374151;padding:10px 0">{mname}</div>',
            unsafe_allow_html=True,
        )
        col3.markdown(
            f'<div style="font-size:12px;color:#6B7280;padding:10px 0">{mtype}</div>',
            unsafe_allow_html=True,
        )
        col4.markdown(
            f'<div style="font-size:12px;color:#6B7280;padding:10px 0">{mat}</div>',
            unsafe_allow_html=True,
        )
        col5.markdown(
            f'<div style="font-size:12px;color:#6B7280;padding:10px 0">{fac or "—"}</div>',
            unsafe_allow_html=True,
        )

        # Status selector (inline edit)
        with col6:
            sc, sb, _ = _STATUS_COLORS.get(status, ("#6B7280", "#F9FAFB", "#E5E7EB"))
            new_status = st.selectbox(
                label="",
                options=_STATUSES,
                index=_STATUSES.index(status) if status in _STATUSES else 0,
                key=f"status_{rec_id}",
                label_visibility="collapsed",
            )
            if new_status != status:
                try:
                    db.update_machine(rec_id, status=new_status)
                    db.log_audit(uid, "machine_status_update",
                                 f"{mid} → {new_status}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        # Edit / Delete buttons
        with col7:
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button("✏️", key=f"edit_{rec_id}", help="Edit machine"):
                    st.session_state[f"_editing_{rec_id}"] = True

            with btn2:
                if can_delete:
                    if st.button("🗑️", key=f"del_{rec_id}", help="Delete machine"):
                        st.session_state[f"_confirm_del_{rec_id}"] = True

        # ── Inline edit form ─────────────────────────────────────
        if st.session_state.get(f"_editing_{rec_id}"):
            with st.form(f"edit_form_{rec_id}"):
                st.markdown(
                    f'<div style="font-size:13px;font-weight:600;color:#1D4ED8;'
                    f'margin-bottom:8px">Editing: {mname}</div>',
                    unsafe_allow_html=True,
                )
                e1, e2 = st.columns(2)
                with e1:
                    e_name = st.text_input("Machine Name", value=mname, key=f"en_{rec_id}")
                    e_mat  = st.selectbox("Material", _MATERIALS,
                                          index=_MATERIALS.index(mat) if mat in _MATERIALS else 0,
                                          key=f"em_{rec_id}")
                with e2:
                    e_type = st.selectbox("Machine Type", _MACHINE_TYPES,
                                          index=_MACHINE_TYPES.index(mtype) if mtype in _MACHINE_TYPES else 0,
                                          key=f"et_{rec_id}")
                    e_loc  = st.text_input("Location", value=m.get("location", ""), key=f"el_{rec_id}")

                e_fac = st.text_input("Factory", value=fac if fac != "—" else "", key=f"ef_{rec_id}")
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.form_submit_button("Save Changes", type="primary"):
                        try:
                            db.update_machine(
                                rec_id,
                                machine_name=e_name.strip(),
                                machine_type=e_type,
                                material=e_mat,
                                factory=e_fac.strip(),
                                location=e_loc.strip(),
                            )
                            db.log_audit(uid, "machine_updated", f"{mid} fields updated")
                            st.session_state.pop(f"_editing_{rec_id}", None)
                            st.success("✅ Machine updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with sc2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.pop(f"_editing_{rec_id}", None)
                        st.rerun()

        # ── Delete confirmation ───────────────────────────────────
        if st.session_state.get(f"_confirm_del_{rec_id}"):
            st.warning(
                f"⚠️ Delete **{mname}** ({mid})? This cannot be undone."
            )
            dc1, dc2, _ = st.columns([1, 1, 3])
            with dc1:
                if st.button("Yes, delete", key=f"confirmdel_{rec_id}", type="primary"):
                    try:
                        db.delete_machine(rec_id)
                        db.log_audit(uid, "machine_deleted", f"{mid} deleted")
                        st.session_state.pop(f"_confirm_del_{rec_id}", None)
                        st.success(f"Machine {mid} deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with dc2:
                if st.button("Cancel", key=f"canceldel_{rec_id}"):
                    st.session_state.pop(f"_confirm_del_{rec_id}", None)
                    st.rerun()

        st.markdown(
            '<div style="border-bottom:1px solid #F1F5F9;margin:2px 0"></div>',
            unsafe_allow_html=True,
        )
