"""Interactive offline dashboard for saved DARE-RUL Phase 8 artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data import EXPERTS, SUBSETS, filtered_fleet, load_phase8_artifacts  # noqa: E402

st.set_page_config(page_title="DARE-RUL | Predictive Maintenance", layout="wide")
st.title("DARE-RUL | Remaining Useful Life Explorer")
st.caption("Offline research dashboard • NASA C-MAPSS FD001–FD004 • Benchmark results, not aviation maintenance advice")

try:
    artifacts = load_phase8_artifacts(ROOT)
except Exception as exc:
    st.error(f"Could not load the saved Phase 8 artifacts: {exc}")
    st.info("Check that results/phase8 contains the prediction, scored, metrics and maintenance CSV files.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    subsets = st.multiselect("C-MAPSS subset", list(SUBSETS), default=list(SUBSETS))
    risk_choices = sorted(artifacts.maintenance["risk_tier"].dropna().astype(str).unique().tolist())
    risks = st.multiselect("Illustrative tier", risk_choices, default=risk_choices)
    query = st.text_input("Search subset or engine ID")
    page = st.radio("Dashboard page", ["Fleet overview", "Model evaluation", "Ensemble behaviour", "SHAP explainability", "Pipeline evidence"])

if not subsets:
    st.warning("Select at least one subset in the sidebar.")
    st.stop()

fleet = filtered_fleet(artifacts, subsets, risks, query)

if page == "Fleet overview":
    st.subheader("Fleet overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Engines in view", f"{len(fleet):,}")
    c2.metric("Critical tier", int((fleet.get("risk_tier", pd.Series(dtype=str)) == "CRITICAL").sum()))
    c3.metric("High tier", int((fleet.get("risk_tier", pd.Series(dtype=str)) == "HIGH").sum()))
    c4.metric("Mean predicted RUL", "—" if fleet.empty else f"{fleet['predicted_rul'].mean():.1f} cycles")
    if not fleet.empty:
        fig = px.histogram(fleet, x="predicted_rul", color="subset", nbins=25, title="Predicted RUL distribution")
        fig.update_layout(xaxis_title="Predicted RUL (cycles)", yaxis_title="Engine count")
        st.plotly_chart(fig, use_container_width=True)
        view_cols = ["subset", "engine_id", "final_cycle", "predicted_rul", "risk_tier", "selected_method", "training_rul_cap", "illustrative_next_step"]
        st.dataframe(fleet[view_cols], use_container_width=True, hide_index=True)
        st.download_button("Download filtered fleet CSV", fleet.to_csv(index=False).encode("utf-8"), "dare_rul_filtered_fleet.csv", "text/csv")
    else:
        st.info("No engines match the current filters.")
    st.warning("CRITICAL/HIGH/MONITOR are illustrative demo tiers, not approved maintenance policy.")

elif page == "Model evaluation":
    st.subheader("Saved Phase 8 evaluation")
    metrics = artifacts.metrics.loc[artifacts.metrics["subset"].isin(subsets)].copy()
    metric_cols = [c for c in ["subset", "selected_method", "test_engines", "rmse", "mae", "nasa_score_sum", "nasa_score_mean"] if c in metrics]
    st.dataframe(metrics[metric_cols], use_container_width=True, hide_index=True)
    fig = px.bar(metrics, x="subset", y="rmse", color="selected_method", title="RMSE by subset (lower is better)")
    st.plotly_chart(fig, use_container_width=True)
    scored = artifacts.scored.loc[artifacts.scored["subset"].isin(subsets)].copy()
    if not scored.empty:
        fig = px.scatter(scored, x="RUL_true", y="predicted_rul", color="subset", hover_data=["engine_id", "selected_method"], title="Predicted versus official test RUL")
        fig.add_shape(type="line", x0=0, y0=0, x1=max(scored["RUL_true"].max(), scored["predicted_rul"].max()), y1=max(scored["RUL_true"].max(), scored["predicted_rul"].max()), line={"dash": "dash"})
        fig.update_layout(xaxis_title="Official test RUL (cycles)", yaxis_title="Predicted RUL (cycles)")
        st.plotly_chart(fig, use_container_width=True)
        fig = px.histogram(scored, x="error_pred_minus_true", color="subset", nbins=35, title="Prediction error distribution")
        st.plotly_chart(fig, use_container_width=True)
    st.warning("These official test results are frozen historical scores. Do not use them to tune a new model and still call this cohort untouched.")
    v2_metrics_path = ROOT / "results" / "phase9" / "ensemble_v2_validation_metrics.csv"
    if v2_metrics_path.is_file():
        st.divider()
        st.subheader("Phase 9 V2 validation comparison")
        st.warning("Exploratory only: this uses the existing Phase 6 validation cohort, which was already used in prior comparisons. These are not official test results.")
        v2_metrics = pd.read_csv(v2_metrics_path)
        v2_metrics = v2_metrics.loc[v2_metrics["subset"].isin(subsets)]
        st.dataframe(v2_metrics[[c for c in ["subset", "method", "rmse", "mae", "nasa_score_mean", "engine_macro_rmse", "engine_macro_mae"] if c in v2_metrics]], use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(v2_metrics, x="subset", y="rmse", color="method", barmode="group", title="Phase 9 V2 validation RMSE comparison"), use_container_width=True)

elif page == "Ensemble behaviour":
    st.subheader("Four experts and adaptive combiner")
    available = artifacts.predictions.loc[artifacts.predictions["subset"].isin(subsets)]
    if available.empty:
        st.info("No engine records match the selected subset filters.")
    else:
        subset = st.selectbox("Subset for engine detail", subsets)
        rows = available.loc[available["subset"] == subset]
        engine_id = st.selectbox("Test engine", sorted(rows["engine_id"].astype(int).tolist()))
        row = rows.loc[rows["engine_id"].astype(int) == int(engine_id)].iloc[0]
        left, right = st.columns(2)
        expert_df = pd.DataFrame({"expert": list(EXPERTS), "prediction_rul": [row[f"pred_{e}"] for e in EXPERTS], "expected_error": [row[f"expected_error_{e}"] for e in EXPERTS], "weight": [row[f"weight_{e}"] for e in EXPERTS]})
        left.metric("Final ensemble RUL", f"{float(row['predicted_rul']):.2f} cycles")
        left.metric("Frozen Phase 8 method", str(row["selected_method"]))
        right.metric("Sum of blending weights", f"{expert_df['weight'].sum():.6f}")
        st.dataframe(expert_df, use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(expert_df, x="expert", y="prediction_rul", title="Individual expert predictions"), use_container_width=True)
        st.plotly_chart(px.bar(expert_df, x="expert", y="weight", title="Adaptive blending weights"), use_container_width=True)
        st.caption("The Phase 8 output records each expert prediction, expected-error estimate and the final weight used by the adaptive combiner.")

elif page == "SHAP explainability":
    st.subheader("End-to-end SHAP for the saved Phase 8 ensemble")
    st.markdown("The explainer perturbs allowed sensor/settings/temporal features and calls the saved experts plus error gates. Identifiers and targets are not explainer inputs. A prediction-parity check must pass before SHAP is shown.")
    available_subsets = [s for s in subsets if (artifacts.predictions["subset"] == s).any()]
    subset = st.selectbox("Subset to explain", available_subsets)
    pred_rows = artifacts.predictions.loc[artifacts.predictions["subset"] == subset]
    engine_id = st.selectbox("Engine to explain", sorted(pred_rows["engine_id"].astype(int).tolist()))
    c1, c2 = st.columns(2)
    background_size = c1.slider("Training background rows", 2, 10, 4)
    permutations = c2.slider("SHAP permutations (more = slower)", 1, 3, 1)
    if st.button("Verify parity and calculate SHAP", type="primary"):
        with st.spinner("Loading saved models, checking parity and computing SHAP. This can take a while."):
            try:
                from dashboard.ensemble_service import SavedEnsembleService
                service = SavedEnsembleService(ROOT)
                parity = service.parity_report(subset, int(engine_id))
                st.write("Prediction parity check", parity)
                if not parity["passed"]:
                    st.error("Saved-model reconstruction does not match the saved output. SHAP has been blocked to avoid a misleading explanation.")
                else:
                    explanation = service.explain_engine(subset, int(engine_id), background_size=background_size, permutations=permutations)
                    st.success("Parity passed. SHAP is a model attribution, not causal proof.")
                    row = pred_rows.loc[pred_rows["engine_id"].astype(int) == int(engine_id)].iloc[0]
                    st.metric("Saved ensemble prediction", f"{float(row['predicted_rul']):.2f} cycles")
                    top = explanation.head(20).sort_values("shap_value_cycles")
                    fig = px.bar(top, x="shap_value_cycles", y="feature", orientation="h", hover_data=["feature_value"], title="Top 20 feature attributions for this engine")
                    fig.update_layout(xaxis_title="SHAP contribution (RUL cycles)", yaxis_title="Input feature")
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(explanation.head(40), use_container_width=True, hide_index=True)
                    st.download_button("Download SHAP attributions", explanation.to_csv(index=False).encode("utf-8"), f"shap_{subset}_engine_{engine_id}.csv", "text/csv")
            except Exception as exc:
                st.error(f"Explainability could not complete: {exc}")
                st.info("Check that models/phase8, Phase 4 parquet features, and scripts/phase7/phase7_core.py are present and consistent with the Phase 8 run.")

else:
    st.subheader("Kafka → Spark Structured Streaming → HDFS evidence")
    st.markdown("The documented benchmark is a local replay/drain test. It does not prove horizontal scaling, concurrent real-time operation, high availability or fault recovery.")
    summary = ROOT / "docs" / "project" / "phase7_streaming_benchmark_summary.md"
    if summary.is_file():
        st.markdown(summary.read_text(encoding="utf-8-sig"))
    upload = st.file_uploader("Optional: load the saved Phase 7 benchmark CSV", type=["csv"])
    if upload is not None:
        bench = pd.read_csv(upload)
        st.dataframe(bench, use_container_width=True, hide_index=True)
        numeric = bench.select_dtypes(include="number").columns.tolist()
        if len(numeric) >= 2:
            x_col = st.selectbox("Workload/size column", numeric)
            y_col = st.selectbox("Runtime/throughput column", [c for c in numeric if c != x_col])
            st.plotly_chart(px.line(bench, x=x_col, y=y_col, markers=True, title=f"{y_col} by {x_col}"), use_container_width=True)
