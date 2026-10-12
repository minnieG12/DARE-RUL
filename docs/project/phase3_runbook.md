# Phase 3 Runbook — Spark + HDFS

Use this guide to reproduce the Phase 3 smoke test. Keep Kafka running while submitting Spark jobs.

## 1. Start and check the services

From `E:\Projects\big data\DARE-RUL`:

```powershell
.\scripts\kafka\start_kafka.ps1
.\scripts\phase3\start_phase3_cluster.ps1
.\scripts\phase3\verify_phase3_cluster.ps1
```

Services:
- Spark Master UI: http://localhost:8080
- Spark Worker UI: http://localhost:8081
- HDFS NameNode UI: http://localhost:9870

Do not use `docker compose down --volumes` on Phase 3; it deletes the HDFS volumes.

## 2. Prepare HDFS project permissions (only if not already set)

```powershell
.\scripts\phase3\prepare_hdfs_permissions.ps1
```

The script uses Hadoop commands `-mkdir`, `-chown`, `-chmod` and `-ls` to prepare `/dare-rul`, `/dare-rul/phase3`, and `/dare-rul/checkpoints/phase3` for the Spark job user. It does not change permissions on HDFS `/`.

## 3. Choose a known Phase 2 topic and a unique run label

```powershell
$Rows = Import-Csv .\docs\project\phase2_matrix_results.csv
$Row = $Rows | Where-Object {
    $_.dataset -eq 'FD001' -and $_.split -eq 'train' -and $_.status -eq 'PASS'
} | Select-Object -First 1

if ($null -eq $Row) { throw 'No passing FD001/train topic was found.' }

$Topic = $Row.topic
$RunLabel = "fd001_train_$(Get-Date -Format yyyyMMdd_HHmmss)"
Write-Host "Topic=$Topic; RunLabel=$RunLabel"
```

## 4. Submit Spark Structured Streaming

```powershell
.\scripts\phase3\run_spark_phase3.ps1 `
    -Topic $Topic `
    -RunLabel $RunLabel `
    -ExpectedMessages 500
```

A new label is required for each run because Spark output paths and streaming checkpoints are specific to the run. Do not delete checkpoints blindly.

The Spark job reads Kafka from earliest offsets, parses the telemetry schema, separates valid from invalid events, writes Parquet to HDFS, checkpoints progress and counts rows back from Parquet.

## 5. Verify output and tests

```powershell
$SummaryPath = ".\results\phase3\$($RunLabel)_summary.json"
$Summary = Get-Content $SummaryPath -Raw | ConvertFrom-Json
$Summary | Format-List

.\scripts\phase3\verify_phase3_output.ps1 -RunLabel $RunLabel

.\.venv\Scripts\python.exe -m pytest .\tests\test_phase3_event_validation.py -q
```

For the recorded smoke test, expected output was 500 valid rows, 0 invalid rows, 0 duplicate engine-cycle pairs, 0 ordering warnings and 5 passing tests. Always use the actual output from a new run.

## Troubleshooting notes

- **Ivy `FileNotFoundException` under `/home/spark/.ivy2/cache`:** the job wrapper now points Ivy at writable `/tmp/dare-rul-ivy`. Keep this setting in the Compose/job entrypoint.
- **HDFS `AccessControlException` at `/`:** Spark runs as user `spark`; execute the permission-preparation script. Do not make `/` world-writable.
- **`NativeCodeLoader` warning:** this local Hadoop image can fall back to built-in Java implementations. It was non-fatal in the passing run.
- **Adaptive query execution notice:** Spark disables AQE for streaming queries; expected and non-fatal here.
- **Kafka AdminClient unused configuration warnings:** appeared while Spark initializes the connector and did not prevent the recorded run from passing.
- If a run fails after creating output/checkpoint directories, use a new run label. Preserve the old paths for debugging until you deliberately decide to clean them.

## Scope limit

The local cluster has one Spark worker and one HDFS DataNode. Phase 3 is an integration prototype, not a scalability or resilience result.
