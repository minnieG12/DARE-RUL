"""Optional Streamlit view for Phase 8 prediction-only maintenance demo.

Run from the repository root: python -m streamlit run scripts/phase8/maintenance_dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.phase8.maintenance_demo import recommendation_for_rul

PREDICTIONS = ROOT / "results" / "phase8" / "test_predictions.csv"

st.set_page_config(page_title="DARE-RUL Maintenance Demo", layout="wide")
st.title("DARE-RUL | Maintenance Decision-Support Demo")
st.caption("Research prototype only. Risk bands are illustrative; this is not an approved aviation maintenance tool.")

if not PREDICTIONS.exists():
    st.error(f"Prediction file not found: {PREDICTIONS}. Run Phase 8 final test evaluation first.")
    st.stop()

frame = pd.read_csv(PREDICTIONS)
required = {"subset", "engine_id", "final_cycle", "selected_method", "predicted_rul"}
if not required.issubset(frame.columns):
    st.error(f"Prediction file is missing columns: {sorted(required - set(frame.columns))}")
    st.stop()
if "RUL_true" in frame.columns:
    st.error("Use the prediction-only test_predictions.csv, not a file containing official targets.")
    st.stop()

with st.sidebar:
    st.header("Demo thresholds")
    critical = st.slider("Critical if predicted RUL <=", min_value=0, max_value=60, value=10)
    high = st.slider("High if predicted RUL <=", min_value=1, max_value=120, value=30)
    subset = st.selectbox("Dataset subset", ["All", "FD001", "FD002", "FD003", "FD004"])
if high <= critical:
    st.error("The high threshold must be greater than the critical threshold.")
    st.stop()

classified = frame.copy()
labels = [recommendation_for_rul(v, critical, high) for v in classified.predicted_rul]
classified["risk_tier"] = [x[0] for x in labels]
classified["illustrative_next_step"] = [x[1] for x in labels]
view = classified if subset == "All" else classified.loc[classified.subset == subset]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Engines shown", len(view))
c2.metric("Critical", int((view.risk_tier == "CRITICAL").sum()))
c3.metric("High", int((view.risk_tier == "HIGH").sum()))
c4.metric("Monitor", int((view.risk_tier == "MONITOR").sum()))

st.subheader("Predicted remaining useful life")
st.bar_chart(view.set_index("engine_id")["predicted_rul"])
st.subheader("Engine-level review queue")
st.dataframe(
    view[["subset", "engine_id", "final_cycle", "selected_method", "predicted_rul", "risk_tier", "illustrative_next_step"]]
    .sort_values("predicted_rul", ascending=True),
    use_container_width=True,
)
st.info("The app reads model predictions only. It does not use official test RUL labels to generate maintenance tiers.")
