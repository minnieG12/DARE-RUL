from dashboard.navigation import DASHBOARD_PAGES, DEFAULT_DASHBOARD_PAGE
from dashboard.evaluation import build_v1_v2_comparison, V1_METHOD, V2_NESTED_METHOD
import pandas as pd


def test_model_evaluation_is_first_landing_page():
    assert DASHBOARD_PAGES[0] == "Model evaluation"
    assert DEFAULT_DASHBOARD_PAGE == "Model evaluation"


def test_dashboard_navigation_has_logical_order():
    assert DASHBOARD_PAGES == (
        "Model evaluation",
        "Fleet overview",
        "Ensemble behaviour",
        "Explainability (SHAP)",
        "Pipeline performance",
        "Project notes",
    )


def test_nested_v1_v2_comparison_uses_actual_nested_method_names():
    metrics = pd.DataFrame([
        {"subset": "FD001", "method": V1_METHOD, "rmse": 16.0, "mae": 12.0},
        {"subset": "FD001", "method": V2_NESTED_METHOD, "rmse": 16.0, "mae": 12.0},
    ])
    result = build_v1_v2_comparison(metrics, ["FD001"])
    assert len(result) == 1
    assert result.loc[0, "Lower RMSE in this run"] == "Tie"
    assert abs(result.loc[0, "V2 − V1 RMSE"]) < 1e-12


def test_nested_v1_v2_comparison_reports_v1_when_v2_is_worse():
    metrics = pd.DataFrame([
        {"subset": "FD002", "method": V1_METHOD, "rmse": 19.4, "mae": 14.4},
        {"subset": "FD002", "method": V2_NESTED_METHOD, "rmse": 19.5, "mae": 14.5},
    ])
    result = build_v1_v2_comparison(metrics, ["FD002"])
    assert result.loc[0, "Lower RMSE in this run"] == "V1"


def test_comparison_returns_empty_when_subset_is_absent():
    metrics = pd.DataFrame([
        {"subset": "FD001", "method": V1_METHOD, "rmse": 16.0, "mae": 12.0},
        {"subset": "FD001", "method": V2_NESTED_METHOD, "rmse": 16.1, "mae": 12.1},
    ])
    assert build_v1_v2_comparison(metrics, ["FD004"]).empty
