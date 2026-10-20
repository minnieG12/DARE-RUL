# Dashboard UI polish notes

This change keeps the same saved artifacts and model interfaces while updating the presentation layer.

- Subtitle now reads: “NASA C-MAPSS FD001–FD004 • Predictive-maintenance research and fleet analytics”.
- Warnings about routine project boundaries are replaced by neutral captions, concise guidance or an expander; actual loading/parity errors still remain visible.
- The streaming page is titled “Streaming Pipeline Performance” and does not display the historical phase-specific report heading.
- The benchmark results table is parsed from the maintained Markdown results table rather than rendering the whole document into the app.
- The page shows workload cards, throughput and elapsed-time charts, the results table, aggregate data-quality metrics, a three-step pipeline diagram and an expandable run-configuration note.
- Streamlit calls use `width="stretch"` to eliminate the deprecation warnings in the current terminal output.
- SHAP supports both a selected-engine view and a small-sample global overview. It continues to require saved-model prediction parity before displaying attributions.

Run the new parser tests before committing. The UI relies on saved Phase 8 model files and Phase 4 feature Parquet files that remain local.
