"""DARE-RUL offline research dashboard with calm visual hierarchy."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data import EXPERTS, SUBSETS, filtered_fleet, load_phase8_artifacts  # noqa: E402
from dashboard.pipeline import read_streaming_benchmark  # noqa: E402

st.set_page_config(page_title="DARE-RUL | RUL Explorer", page_icon="⚙️", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1500px; padding-top: 1.45rem; padding-bottom: 2.2rem;}
      [data-testid="stAppViewContainer"] {background: #f7f9fc;}
      [data-testid="stSidebar"] {background: #f0f4f9;}
      h1, h2, h3 {color: #1d2d50; letter-spacing: -0.02em;}
      h1 {font-size: 2.15rem !important; font-weight: 760 !important;}
      h2 {font-size: 1.55rem !important;}
      [data-testid="stMetric"] {background: #ffffff; border: 1px solid #e2eaf3; border-radius: 13px; padding: 14px 16px;}
      [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px; border-color: #e2eaf3; background: #ffffff;}
      .dare-subtitle {color: #68758b; font-size: 0.98rem; margin-top: -0.35rem; margin-bottom: 1.1rem;}
      .dare-kicker {color: #47607d; font-size: 0.83rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;}
      .dare-pipeline-node {background: #ffffff; border: 1px solid #dfe8f2; border-radius: 12px; padding: 16px 14px; min-height: 126px;}
      .dare-pipeline-node h4 {color: #1d2d50; margin: 0 0 7px 0; font-size: 1rem;}
      .dare-pipeline-node p {color: #697990; margin: 0; font-size: 0.9rem; line-height: 1.42;}
      .dare-footer {color: #7b8798; font-size: 0.8rem; padding-top: 1.2rem; border-top: 1px solid #e6ebf2; margin-top: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("DARE-RUL | Remaining Useful Life Explorer")
st.markdown(
    '<div class="dare-subtitle">NASA C-MAPSS FD001–FD004 • Predictive-maintenance research and fleet analytics</div>',
    unsafe_allow_html=True,
)

try:
    artifacts = load_phase8_artifacts(ROOT)
except Exception as exc:
    st.error(f"The saved evaluation files could not be loaded: {exc}")
    st.info("Confirm the four saved CSV files exist under results/phase8, then restart the dashboard.")
    st.stop()

with st.sidebar:
    st.markdown("### Explorer controls")
    subsets = st.multiselect("Dataset subset", list(SUBSETS), default=list(SUBSETS))
    risk_choices = sorted(artifacts.maintenance["risk_tier"].dropna().astype(str).unique().tolist())
    risks = st.multiselect("Demonstration tier", risk_choices, default=risk_choices)
    query = st.text_input("Find an engine", placeholder="Enter subset or engine ID")
    st.divider()
    page = st.radio(
        "View",
        ["Fleet overview", "Model evaluation", "Ensemble behaviour", "Explainability (SHAP)", "Pipeline performance", "Project notes"],
    )

if not subsets:
    st.info("Choose at least one dataset subset to populate the explorer.")
    st.stop()

fleet = filtered_fleet(artifacts, subsets, risks, query)


def _format_engine_count(value: int) -> str:
    return f"{int(value):,}"


def _v1_v2_comparison(metrics: pd.DataFrame, selected_subsets: Iterable[str]) -> pd.DataFrame:
    required = {"subset", "method", "rmse", "mae"}
    if not required.issubset(metrics.columns):
        return pd.DataFrame()
    frame = metrics.loc[
        metrics["subset"].isin(list(selected_subsets))
        & metrics["method"].isin(["V1_adaptive_error_gate", "V2_bounded_shrunk"])
    ].copy()
    if frame.empty:
        return pd.DataFrame()
    wide = frame.pivot(index="subset", columns="method", values=["rmse", "mae"])
    needed = [(m, method) for m in ("rmse", "mae") for method in ("V1_adaptive_error_gate", "V2_bounded_shrunk")]
    if any(c not in wide.columns for c in needed):
        return pd.DataFrame()
    result = pd.DataFrame(index=wide.index)
    result["V1 RMSE"] = wide[("rmse", "V1_adaptive_error_gate")]
    result["V2 RMSE"] = wide[("rmse", "V2_bounded_shrunk")]
    result["V2 − V1 RMSE"] = result["V2 RMSE"] - result["V1 RMSE"]
    result["V1 MAE"] = wide[("mae", "V1_adaptive_error_gate")]
    result["V2 MAE"] = wide[("mae", "V2_bounded_shrunk")]
    result["V2 − V1 MAE"] = result["V2 MAE"] - result["V1 MAE"]
    result["Lower RMSE in this run"] = result.apply(lambda r: "V2" if r["V2 − V1 RMSE"] < 0 else ("Tie" if abs(r["V2 − V1 RMSE"]) < 1e-12 else "V1"), axis=1)
    result.index.name = "Subset"
    return result.reset_index()


if page == "Fleet overview":
    st.subheader("Fleet overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Engines in view", _format_engine_count(len(fleet)))
    c2.metric("Critical demo tier", int((fleet.get("risk_tier", pd.Series(dtype=str)) == "CRITICAL").sum()))
    c3.metric("High demo tier", int((fleet.get("risk_tier", pd.Series(dtype=str)) == "HIGH").sum()))
    c4.metric("Mean predicted RUL", "—" if fleet.empty else f"{fleet['predicted_rul'].mean():.1f} cycles")
    if not fleet.empty:
        fig = px.histogram(fleet, x="predicted_rul", color="subset", nbins=25, title="Predicted RUL distribution")
        fig.update_layout(xaxis_title="Predicted RUL (cycles)", yaxis_title="Engine count", legend_title="Subset")
        st.plotly_chart(fig, width="stretch")
        view_cols = ["subset", "engine_id", "final_cycle", "predicted_rul", "risk_tier", "selected_method", "training_rul_cap", "illustrative_next_step"]
        st.dataframe(fleet[view_cols], width="stretch", hide_index=True)
        st.download_button("Export filtered fleet (CSV)", fleet.to_csv(index=False).encode("utf-8"), "dare_rul_filtered_fleet.csv", "text/csv")
    else:
        st.info("No engines match these filters. Adjust the subset, tier or search field to see more results.")
    st.caption("Priority tiers are configurable demonstration categories for comparing model outputs.")

elif page == "Model evaluation":
    st.subheader("Model evaluation")
    st.caption("Saved evaluation snapshot • RMSE, MAE and the PHM08/NASA asymmetric score are reported by subset.")
    metrics = artifacts.metrics.loc[artifacts.metrics["subset"].isin(subsets)].copy()
    metric_cols = [c for c in ["subset", "selected_method", "test_engines", "rmse", "mae", "nasa_score_sum", "nasa_score_mean"] if c in metrics]
    st.dataframe(metrics[metric_cols], width="stretch", hide_index=True)
    if not metrics.empty:
        fig = px.bar(metrics, x="subset", y="rmse", color="selected_method", title="RMSE by subset (lower is better)")
        st.plotly_chart(fig, width="stretch")
    scored = artifacts.scored.loc[artifacts.scored["subset"].isin(subsets)].copy()
    if not scored.empty:
        fig = px.scatter(scored, x="RUL_true", y="predicted_rul", color="subset", hover_data=["engine_id", "selected_method"], title="Predicted versus reference RUL")
        max_value = max(float(scored["RUL_true"].max()), float(scored["predicted_rul"].max()))
        fig.add_shape(type="line", x0=0, y0=0, x1=max_value, y1=max_value, line={"dash": "dash"})
        fig.update_layout(xaxis_title="Reference RUL (cycles)", yaxis_title="Predicted RUL (cycles)")
        st.plotly_chart(fig, width="stretch")
        fig = px.histogram(scored, x="error_pred_minus_true", color="subset", nbins=35, title="Prediction error distribution")
        st.plotly_chart(fig, width="stretch")
    st.caption("The saved test scores document the frozen evaluation run. New model variants are compared with validation experiments.")

    v2_metrics_path = ROOT / "results" / "phase9" / "ensemble_v2_validation_metrics.csv"
    if v2_metrics_path.is_file():
        st.divider()
        st.subheader("Adaptive ensemble experiment")
        st.caption("V1 and V2 are compared on the existing engine-level validation cohort for continuity with earlier experiments.")
        v2_metrics = pd.read_csv(v2_metrics_path)
        v2_metrics = v2_metrics.loc[v2_metrics["subset"].isin(subsets)]
        comparison = _v1_v2_comparison(v2_metrics, subsets)
        if not comparison.empty:
            st.dataframe(comparison.round(4), width="stretch", hide_index=True)
            delta_fig = px.bar(
                comparison, x="Subset", y="V2 − V1 RMSE", color="Lower RMSE in this run",
                title="RMSE change from V1 to V2 (cycles; values below zero favour V2)",
            )
            delta_fig.add_hline(y=0, line_dash="dash", line_color="#7b8798")
            st.plotly_chart(delta_fig, width="stretch")
        visible = [c for c in ["subset", "method", "rmse", "mae", "nasa_score_mean", "engine_macro_rmse", "engine_macro_mae"] if c in v2_metrics]
        st.dataframe(v2_metrics[visible].round(4), width="stretch", hide_index=True)
        with st.expander("How to interpret this comparison"):
            st.write("This experiment reuses the existing Phase 6 validation cohort. It is useful for understanding the current V1/V2 behaviour; an independent model-selection estimate requires a separate grouped or nested validation design.")

elif page == "Ensemble behaviour":
    st.subheader("Expert predictions and adaptive blending")
    available = artifacts.predictions.loc[artifacts.predictions["subset"].isin(subsets)]
    available_subsets = [s for s in subsets if (available["subset"] == s).any()]
    if available.empty:
        st.info("No engine records match the selected subset filters.")
    else:
        subset = st.selectbox("Dataset subset for engine detail", available_subsets)
        rows = available.loc[available["subset"] == subset]
        engine_id = st.selectbox("Engine", sorted(rows["engine_id"].astype(int).tolist()))
        row = rows.loc[rows["engine_id"].astype(int) == int(engine_id)].iloc[0]
        left, right = st.columns(2)
        expert_df = pd.DataFrame({"Expert": list(EXPERTS), "Predicted RUL (cycles)": [row[f"pred_{e}"] for e in EXPERTS], "Estimated error": [row[f"expected_error_{e}"] for e in EXPERTS], "Blend weight": [row[f"weight_{e}"] for e in EXPERTS]})
        left.metric("Final ensemble RUL", f"{float(row['predicted_rul']):.2f} cycles")
        left.metric("Selected method", str(row["selected_method"]))
        right.metric("Weight total", f"{expert_df['Blend weight'].sum():.6f}")
        st.dataframe(expert_df, width="stretch", hide_index=True)
        st.plotly_chart(px.bar(expert_df, x="Expert", y="Predicted RUL (cycles)", title="Individual expert predictions"), width="stretch")
        st.plotly_chart(px.bar(expert_df, x="Expert", y="Blend weight", title="Adaptive blending weights"), width="stretch")
        st.caption("The engine view shows the saved expert predictions, expected-error estimates and blend weights used in the recorded evaluation.")

elif page == "Explainability (SHAP)":
    st.subheader("Explainability for the complete ensemble")
    st.caption("Feature contributions are measured in RUL cycles relative to a sample of training features. Explanations are calculated for the full expert-and-gate prediction function.")
    available_subsets = [s for s in subsets if (artifacts.predictions["subset"] == s).any()]
    if not available_subsets:
        st.info("No predictions are available for these subset filters.")
        st.stop()
    subset = st.selectbox("Dataset subset to explain", available_subsets)
    pred_rows = artifacts.predictions.loc[artifacts.predictions["subset"] == subset]
    explanation_mode = st.radio("Explanation view", ["Selected engine", "Global overview (small sample)"], horizontal=True)
    if explanation_mode == "Selected engine":
        engine_ids = [st.selectbox("Engine", sorted(pred_rows["engine_id"].astype(int).tolist()))]
    else:
        n_engines = st.slider("Number of engines to sample", min_value=2, max_value=min(8, len(pred_rows)), value=min(3, len(pred_rows)))
        engine_ids = sorted(pred_rows["engine_id"].astype(int).unique().tolist())[:n_engines]
        st.caption("The global view averages absolute attributions over a small, deterministic sample of final-cycle engine records.")
    c1, c2 = st.columns(2)
    background_size = c1.slider("Training background rows", 2, 10, 4)
    permutations = c2.slider("Permutation budget", 1, 3, 1, help="Larger budgets take longer and may give more stable estimates.")
    if st.button("Calculate SHAP explanation", type="primary"):
        with st.spinner("Checking prediction parity and calculating explanations..."):
            try:
                from dashboard.ensemble_service import SavedEnsembleService
                service = SavedEnsembleService(ROOT)
                parity_rows = [service.parity_report(subset, int(engine_id)) for engine_id in engine_ids]
                parity = pd.DataFrame([
                    {"engine_id": int(engine_id), **report}
                    for engine_id, report in zip(engine_ids, parity_rows)
                ])
                st.dataframe(parity, width="stretch", hide_index=True)
                if not all(row["passed"] for row in parity_rows):
                    st.error("Prediction parity requires review before feature explanations can be displayed.")
                else:
                    explanations = []
                    for engine_id in engine_ids:
                        result = service.explain_engine(subset, int(engine_id), background_size=background_size, permutations=permutations)
                        result["engine_id"] = int(engine_id)
                        explanations.append(result)
                    all_explanations = pd.concat(explanations, ignore_index=True)
                    st.success("Explanation calculated successfully using the saved ensemble and training-feature background.")
                    if explanation_mode == "Selected engine":
                        row = pred_rows.loc[pred_rows["engine_id"].astype(int) == int(engine_ids[0])].iloc[0]
                        st.metric("Saved ensemble prediction", f"{float(row['predicted_rul']):.2f} cycles")
                        top = all_explanations.head(20).sort_values("shap_value_cycles")
                        fig = px.bar(top, x="shap_value_cycles", y="feature", orientation="h", hover_data=["feature_value"], title="Local feature contributions")
                        fig.update_layout(xaxis_title="SHAP contribution (RUL cycles)", yaxis_title="Input feature")
                        st.plotly_chart(fig, width="stretch")
                        st.dataframe(all_explanations.drop(columns=["engine_id"]).head(40), width="stretch", hide_index=True)
                        download_name = f"shap_{subset}_engine_{engine_ids[0]}.csv"
                    else:
                        global_view = (
                            all_explanations.groupby("feature", as_index=False)
                            .agg(mean_abs_shap_cycles=("absolute_shap_value", "mean"), mean_shap_cycles=("shap_value_cycles", "mean"))
                            .sort_values("mean_abs_shap_cycles", ascending=False)
                        )
                        fig = px.bar(global_view.head(20).sort_values("mean_abs_shap_cycles"), x="mean_abs_shap_cycles", y="feature", orientation="h", title="Global overview: mean absolute SHAP contribution")
                        fig.update_layout(xaxis_title="Mean absolute SHAP contribution (RUL cycles)", yaxis_title="Input feature")
                        st.plotly_chart(fig, width="stretch")
                        st.dataframe(global_view, width="stretch", hide_index=True)
                        download_name = f"shap_global_{subset}_{len(engine_ids)}_engines.csv"
                    st.download_button("Export SHAP results (CSV)", all_explanations.to_csv(index=False).encode("utf-8"), download_name, "text/csv")
                    st.caption("Attributions describe model behaviour relative to the chosen training background; they are not causal effects.")
            except Exception as exc:
                st.error(f"The explanation could not be completed: {exc}")
                st.info("Confirm the saved Phase 8 models, Phase 4 feature tables, and original phase7_core.py are present and consistent.")

elif page == "Pipeline performance":
    st.subheader("Streaming Pipeline Performance")
    st.caption("Local Kafka → Spark Structured Streaming → HDFS replay/drain benchmark")
    summary_path = ROOT / "docs" / "project" / "phase7_streaming_benchmark_summary.md"
    try:
        benchmark = read_streaming_benchmark(summary_path)
    except Exception as exc:
        st.error(f"The recorded benchmark table could not be loaded: {exc}")
        st.info("Check that the maintained benchmark summary contains the workload results table.")
        st.stop()

    benchmark = benchmark.sort_values("requested_messages").reset_index(drop=True)
    cards = st.columns(len(benchmark))
    for col, row in zip(cards, benchmark.itertuples(index=False)):
        with col.container(border=True):
            st.markdown(f"#### {int(row.requested_messages):,} messages")
            st.success(str(row.status))
            m1, m2 = st.columns(2)
            m1.metric("Elapsed", f"{float(row.elapsed_seconds):.2f} s")
            m2.metric("Throughput", f"{float(row.rows_per_second):.2f} rows/s")

    left, right = st.columns(2)
    with left:
        fig = px.bar(benchmark, x="workload_label", y="rows_per_second", text="rows_per_second", title="End-to-end throughput")
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(xaxis_title="Requested messages", yaxis_title="Rows per second")
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = px.line(benchmark, x="workload_label", y="elapsed_seconds", markers=True, text="elapsed_seconds", title="Spark/HDFS elapsed time")
        fig.update_traces(texttemplate="%{text:.2f} s", textposition="top center")
        fig.update_layout(xaxis_title="Requested messages", yaxis_title="Elapsed time (seconds)")
        st.plotly_chart(fig, width="stretch")

    table = benchmark[["requested_messages", "delivered", "valid_hdfs_rows", "invalid_rows", "duplicate_engine_cycle_pairs", "cycle_order_warnings", "elapsed_seconds", "rows_per_second", "status"]].rename(columns={
        "requested_messages": "Requested messages", "delivered": "Delivered", "valid_hdfs_rows": "Valid HDFS rows",
        "invalid_rows": "Invalid rows", "duplicate_engine_cycle_pairs": "Duplicate engine-cycle pairs",
        "cycle_order_warnings": "Cycle-order warnings", "elapsed_seconds": "Elapsed (s)",
        "rows_per_second": "Approx. rows/s", "status": "Status",
    })
    st.subheader("Benchmark results")
    st.dataframe(table, width="stretch", hide_index=True)

    total_requested = int(benchmark["requested_messages"].sum())
    total_delivered = int(benchmark["delivered"].sum())
    total_valid = int(benchmark["valid_hdfs_rows"].sum())
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total requested", f"{total_requested:,}")
    c2.metric("Total delivered", f"{total_delivered:,}")
    c3.metric("Valid output rows", f"{total_valid:,}")
    c4.metric("Invalid rows", int(benchmark["invalid_rows"].sum()))
    c5.metric("Duplicate pairs", int(benchmark["duplicate_engine_cycle_pairs"].sum()))
    if ((benchmark["requested_messages"] == benchmark["delivered"]).all()
            and (benchmark["requested_messages"] == benchmark["valid_hdfs_rows"]).all()
            and (benchmark[["invalid_rows", "duplicate_engine_cycle_pairs", "cycle_order_warnings"]] == 0).all().all()
            and (benchmark["status"].str.upper() == "PASS").all()):
        st.success("All recorded delivery and output-integrity checks passed for these workloads.")
    else:
        st.info("Review the table above for any workload whose output checks differ from the expected counts.")

    st.subheader("How the pipeline works")
    flow = st.columns(3)
    nodes = [
        ("1 · Kafka replay", "Send recorded telemetry events for the selected workload."),
        ("2 · Spark Structured Streaming", "Process records and apply the event-validation rules."),
        ("3 · HDFS / Parquet", "Write outputs and verify delivered rows and data quality."),
    ]
    for col, (title, description) in zip(flow, nodes):
        with col.container(border=True):
            st.markdown(f"#### {title}")
            st.write(description)
    with st.expander("Run configuration and interpretation"):
        st.write("Recorded environment: one local Spark worker and one HDFS DataNode. The measurements show end-to-end replay/drain behaviour for this configuration.")
        st.write("Throughput is calculated as requested messages divided by measured Spark/HDFS elapsed time; it is not a producer-only rate.")

elif page == "Project notes":
    st.subheader("Project notes and data context")
    st.write("DARE-RUL studies remaining-useful-life estimates on the NASA C-MAPSS FD001–FD004 simulated turbofan benchmark.")
    st.write("The dashboard reads saved project artifacts; opening it does not train models or rerun official test evaluation.")
    st.write("The demonstration priority tiers are configurable categories for exploring predicted RUL. They are not operational maintenance instructions.")
    st.write("The streaming figures are local replay/drain measurements. Cluster size and run settings are recorded alongside the benchmark evidence.")
    st.write("The original research protocol and literature-based novelty assessment are tracked separately in the project documentation.")

st.markdown('<div class="dare-footer">DARE-RUL • Remaining Useful Life Explorer • Simulated-engine research benchmark</div>', unsafe_allow_html=True)
