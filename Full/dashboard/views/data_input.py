import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import predict, parse_prediction, predict_batch

MILL_SAMPLE_COLS = ["case", "run", "time", "DOC", "feed", "material",
                    "smcAC__mean", "smcAC__rms", "smcAC__std",
                    "smcDC__mean", "smcDC__rms", "smcDC__std",
                    "vib_table__mean", "vib_table__rms",
                    "vib_spindle__mean", "vib_spindle__rms",
                    "AE_table__mean", "AE_table__rms",
                    "AE_spindle__mean", "AE_spindle__rms",
                    "VB_lag1", "VB_lag2", "run_norm"]

def render():
    st.markdown("<div class='section-heading'>📂 Data Input</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📤 Upload CSV", "✏️ Manual Input"])

    # ── Tab 1: CSV Upload ─────────────────────────────────────────
    with tab1:
        st.markdown("<div class='panel-card'><div class='panel-title'>Upload Dataset for Batch Prediction</div>", unsafe_allow_html=True)
        st.info("Upload a CSV matching master_features.csv column format. The backend predict_batch() will run on all rows.")

        uploaded = st.file_uploader("Drop CSV file here", type=["csv"], key="di_upload")
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.session_state.uploaded_df = df
                st.success(f"✅ Loaded {len(df)} rows × {len(df.columns)} columns")

                c1, c2, c3 = st.columns(3)
                c1.metric("Rows", len(df))
                c2.metric("Columns", len(df.columns))
                c3.metric("Missing Values", int(df.isnull().sum().sum()))

                st.dataframe(df.head(8), use_container_width=True, hide_index=True)

                if st.button("▶ Run Batch Prediction", use_container_width=True, key="di_batch"):
                    with st.spinner("Running batch prediction via backend…"):
                        result_df = predict_batch(df)
                    st.success("✅ Batch prediction complete!")
                    show_cols = [c for c in ["case", "run", "time", "VB",
                                             "VB_Predicted", "RUL_Predicted",
                                             "Tool_Health_Score", "Wear_Level",
                                             "Maintenance_Action"] if c in result_df.columns]
                    st.dataframe(result_df[show_cols], use_container_width=True, hide_index=True)

                    csv_out = result_df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Download Results CSV", csv_out,
                                       "batch_predictions.csv", "text/csv",
                                       use_container_width=True, key="di_dl")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.markdown("**Expected columns:**")
            st.code(", ".join(MILL_SAMPLE_COLS))

            # Quick-load the existing master_features.csv
            master_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                       "tool-wear-ai", "data", "processed", "master_features.csv")
            if os.path.exists(master_path) and st.button("Load master_features.csv (demo)", key="di_load_demo"):
                df = pd.read_csv(master_path)
                st.session_state.uploaded_df = df
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 2: Manual Input ───────────────────────────────────────
    with tab2:
        st.markdown("<div class='panel-card'><div class='panel-title'>Manual Sensor Entry → Predict</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Machining Parameters**")
            material = st.selectbox("Material", ["Cast Iron (1)", "Steel (2)"], key="mi_mat")
            doc      = st.number_input("Depth of Cut (mm)", value=0.75, step=0.25, key="mi_doc")
            feed     = st.number_input("Feed Rate (mm/rev)", value=0.5, step=0.05, key="mi_feed")
            time_val = st.number_input("Machining Time (min)", value=25.0, step=1.0, key="mi_time")
            vb_lag1  = st.number_input("VB Lag 1 (mm)", value=0.0, step=0.01, key="mi_lag1")
            vb_lag2  = st.number_input("VB Lag 2 (mm)", value=0.0, step=0.01, key="mi_lag2")
            run_norm = st.slider("Run Position [0-1]", 0.0, 1.0, 0.5, key="mi_run")
        with c2:
            st.markdown("**Sensor Readings + AI4I Inputs**")
            smcAC_mean = st.number_input("smcAC mean",        value=-0.165, format="%.3f", key="mi_smcac")
            smcDC_mean = st.number_input("smcDC mean",        value=6.20,   format="%.3f", key="mi_smcdc")
            vib_t_mean = st.number_input("vib_table mean",    value=0.92,   format="%.3f", key="mi_vibt")
            vib_s_mean = st.number_input("vib_spindle mean",  value=0.40,   format="%.3f", key="mi_vibs")
            ae_t_mean  = st.number_input("AE_table mean",     value=0.22,   format="%.3f", key="mi_aet")
            ae_s_mean  = st.number_input("AE_spindle mean",   value=0.31,   format="%.3f", key="mi_aes")
            st.markdown("---")
            air_temp  = st.number_input("Air Temperature (K)", value=298.1, key="mi_air")
            proc_temp = st.number_input("Process Temperature (K)", value=308.6, key="mi_proc")
            rpm       = st.number_input("Rotational Speed (rpm)", value=1551, key="mi_rpm")
            torque    = st.number_input("Torque (Nm)", value=42.8, key="mi_torque")
            tool_wear = st.number_input("Tool Wear (min)", value=0.0, key="mi_twear")
            machine_type = st.selectbox("Machine Type", ["M", "L", "H"], index=0, key="mi_mtype")

        if st.button("Submit & Predict", use_container_width=True, key="mi_submit"):
            mat_int = 1 if "Cast Iron" in material else 2
            payload = dict(
                smcAC_mean=smcAC_mean, smcAC_rms=abs(smcAC_mean)*1.01, smcAC_std=0.12,
                smcDC_mean=smcDC_mean, smcDC_rms=smcDC_mean*1.01,      smcDC_std=0.08,
                vib_table_mean=vib_t_mean,   vib_table_rms=vib_t_mean*1.02,
                vib_spindle_mean=vib_s_mean, vib_spindle_rms=vib_s_mean*1.02,
                AE_table_mean=ae_t_mean,     AE_table_rms=ae_t_mean*1.02,
                AE_spindle_mean=ae_s_mean,   AE_spindle_rms=ae_s_mean*1.02,
                time=time_val, DOC=doc, feed=feed, material=mat_int,
                VB_lag1=vb_lag1, VB_lag2=vb_lag2, run_norm=run_norm,
                air_temp=air_temp, proc_temp=proc_temp, rpm=rpm,
                torque=torque, tool_wear=tool_wear, machine_type=machine_type,
            )
            with st.spinner("Predicting…"):
                raw = predict(payload)
            if raw.get("source") == "error":
                st.error(raw.get("error"))
            else:
                parsed = parse_prediction(raw)
                st.session_state.prediction = parsed
                st.success(
                    f"✅ VB={parsed['vb']:.4f} mm | RUL={parsed['rul']:.2f} min | "
                    f"Failure Risk={parsed['failure_risk']}% | Action={parsed['action']}"
                )
        st.markdown("</div>", unsafe_allow_html=True)
