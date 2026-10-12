# DARE-RUL Phase 2 Completion Pack

## Purpose
Run an isolated ingestion/consumer check for all eight combinations of FD001-FD004 and train/test. Each run uses a unique Kafka topic so old messages cannot be mistaken for messages sent in the current test.

## Extract
Extract this ZIP into `E:\Projects\big data\DARE-RUL` and allow the two Kafka Python scripts and the initial run-summary files to be replaced. The summary is corrected to explain why the shared-topic consumer run must be re-tested with isolated topics. These updated scripts add a `--topic` option; their previous default topic stays `cmapss-telemetry`.

## Run
From PowerShell at the repository root:

```powershell
.\scripts\kafka\phase2_matrix_test.ps1
```

The default tests 500 messages per dataset/split combination at a target of 100 messages/second. To increase the sample: `-MessagesPerScenario 1000`.

Results are saved to `results/phase2/matrix_<run-id>/` (per-process stdout/stderr logs and CSV) and `docs/project/phase2_matrix_results.csv` (trackable summary). The script fails at the end if any of the eight cases does not pass.

## Safety
- Does not modify or delete the dataset.
- Does not delete existing Kafka topics or volumes.
- Creates eight uniquely named test topics; old test topics remain as evidence.
- Telemetry excludes RUL labels.
- Do not label Phase 2 complete until results CSV has eight PASS rows.
