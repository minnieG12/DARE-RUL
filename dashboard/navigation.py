"""Dashboard navigation order and landing page for DARE-RUL."""

DASHBOARD_PAGES = (
    "Model evaluation",
    "Fleet overview",
    "Ensemble behaviour",
    "Explainability (SHAP)",
    "Pipeline performance",
    "Project notes",
)

DEFAULT_DASHBOARD_PAGE = "Model evaluation"

PAGE_FLOW_DESCRIPTION = (
    "Review model results first, then inspect engine-level predictions, "
    "understand ensemble behaviour, explore SHAP explanations, and finally "
    "review the data-processing pipeline."
)
