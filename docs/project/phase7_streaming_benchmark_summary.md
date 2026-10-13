# Phase 7 Streaming Scalability Benchmark

- **Recorded/updated:** 2026-10-13
- **Status:** PASS for the three required workload sizes, based on the saved benchmark CSV and the validation checks below.
- **Pipeline:** Kafka message replay -> Spark Structured Streaming -> HDFS output verification.
- **Workloads:** 500, 5,000 and 20,000 messages.

## Results

| Requested messages | Delivered | Valid HDFS rows | Invalid rows | Duplicate engine-cycle pairs | Cycle-order warnings | Spark/HDFS elapsed (s) | Approx. end-to-end rows/s | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 500 | 500 | 500 | 0 | 0 | 0 | 29.33 | 17.05 | PASS |
| 5000 | 5000 | 5000 | 0 | 0 | 0 | 59.35 | 84.25 | PASS |
| 20000 | 20000 | 20000 | 0 | 0 | 0 | 151.77 | 131.78 | PASS |

Approximate rows/second is calculated as requested messages divided by the recorded Spark/HDFS elapsed time. It is an end-to-end replay/drain rate for this local run, not a pure Kafka producer rate.

## Data-quality checks

For each reported workload, the saved CSV was checked for: delivered messages matching the requested count; valid HDFS rows matching the requested count; zero invalid rows; zero duplicate engine-cycle pairs; zero cycle-order warnings; and a `PASS` status.

## Scope and limitations

- The benchmark ran on the current local setup with one Spark worker and one HDFS DataNode.
- This is a controlled replay/drain benchmark. It does not establish horizontal scaling, concurrent real-time ingestion, fault recovery, or production reliability.
- The stream benchmark uses the configured FD001 training telemetry; it is not the official C-MAPSS test-set evaluation.
- Official test RUL targets must remain reserved for final evaluation after the RUL-cap and model-selection protocol is frozen.

## Reproduction

```powershell
.\\scripts\\kafka\\start_kafka.ps1
.\\scripts\\phase3\\start_phase3_cluster.ps1
.\\scripts\\phase3\\verify_phase3_cluster.ps1
.\\scripts\\phase7\\benchmark_streaming.ps1 -Sizes 500,5000,20000
```

