# DARE-RUL Phase 3: Spark Structured Streaming + HDFS

This pack adds a small, Docker-based Spark cluster and HDFS storage to the existing DARE-RUL repository.

## Why this design

- Keep your existing Kafka and ZooKeeper running.
- Run Spark 3.5.1 in Docker (the official `spark:3.5.1` image includes Java 11 and Python 3), so do not install PySpark into the Windows virtual environment for this phase.
- Run a Spark master + worker and a Hadoop HDFS NameNode + DataNode on the existing Kafka Docker network.
- Read a clean Phase 2 topic using Spark Structured Streaming.
- Parse the JSON telemetry, route valid records to Parquet in HDFS, route invalid records separately, and write checkpoints to HDFS.
- Store a local run summary under `results/phase3` if the mounted directory is writable.

The official Spark Kafka connector for Spark 3.5.1 is loaded with `--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1`.

## Existing repository assumptions

- Project root: `E:\Projects\big data\DARE-RUL`
- Kafka Compose file: `docker/kafka/compose.yaml`
- Kafka network name created by that file: `dare-rul-phase2_dare-rul-net`
- Phase 2 results: `docs/project/phase2_matrix_results.csv`
- Local raw data folder: `data/CMAPSSData` (not copied or modified by this pack)

## Step 0 — Confirm Phase 2 milestone is pushed

Your latest logs show commit `a909029` pushed to `origin/main`, with all 8 dataset/split scenarios passing. Tag the milestone once:

```powershell
git tag -a phase-2-complete -m "Phase 2 Kafka ingestion matrix passed for FD001-FD004 train/test"
git push origin phase-2-complete
```

If the tag already exists, do not force-recreate it; check `git tag` first.

## Step 1 — Extract this pack

Extract the zip into the existing repo root. It adds only Phase 3 files and does not contain the C-MAPSS dataset.

## Step 2 — Check the shared network

```powershell
docker network ls --format "{{.Name}}" | Select-String "dare-rul-phase2_dare-rul-net"
```

If found, continue. If not found, start Kafka again using:

```powershell
.\scripts\kafka\start_kafka.ps1
```

Then check the network again.

## Step 3 — Start Spark and HDFS

```powershell
.\scripts\phase3\start_phase3_cluster.ps1
```

This pulls the pinned images the first time, then starts Spark Master/Worker and HDFS NameNode/DataNode. First-time image pulls may take several minutes.

Web UIs when started:
- Spark Master: http://localhost:8080
- Spark Worker: http://localhost:8081
- HDFS NameNode: http://localhost:9870

Verify containers and HDFS:

```powershell
docker compose -f .\docker\phase3\compose.yaml ps
.\scripts\phase3\verify_phase3_cluster.ps1
```

Do not run `docker compose down --volumes` for the Phase 3 stack; that would remove HDFS stored data.

## Step 4 — Choose a clean Phase 2 topic

```powershell
$row = Import-Csv .\docs\project\phase2_matrix_results.csv |
    Where-Object { $_.dataset -eq 'FD001' -and $_.split -eq 'train' } |
    Select-Object -First 1
$Topic = $row.topic
$Topic
```

The matrix creates a unique topic per dataset/split containing exactly 500 test messages. We use that topic so Spark has a known input batch.

## Step 5 — Run Spark Structured Streaming

Choose a unique label for this run:

```powershell
$RunLabel = "fd001_train_$(Get-Date -Format yyyyMMdd_HHmmss)"
```

Run the one-off Spark job on the Spark worker cluster:

```powershell
.\scripts\phase3\run_spark_phase3.ps1 -Topic $Topic -RunLabel $RunLabel -ExpectedMessages 500
```

What happens:
1. Spark reads Kafka messages from the beginning of that clean topic.
2. Spark parses the JSON fields and validates required telemetry fields.
3. Valid records are stored as Parquet at `hdfs://namenode:9000/dare-rul/phase3/<RunLabel>/parquet`.
4. Invalid records, if any, are stored separately under `/invalid`.
5. Streaming checkpoints are stored under `hdfs://namenode:9000/dare-rul/checkpoints/phase3/<RunLabel>/`.
6. The job checks count, duplicate engine-cycle pairs, cycle ordering by Kafka offset, and target leakage.

Use a new `$RunLabel` for a new run. Existing checkpoints intentionally cause a refusal so we don't accidentally mix two runs.

## Step 6 — Verify the HDFS output

```powershell
.\scripts\phase3\verify_phase3_output.ps1 -RunLabel $RunLabel
```

Expected for the selected 500-event topic:
- valid rows: 500
- invalid rows: 0
- duplicate engine-cycle rows: 0
- cycle-order warnings: 0
- Spark job status: PASS

HDFS CLI output should show Parquet files at `/dare-rul/phase3/<RunLabel>/parquet` and the checkpoint folders at `/dare-rul/checkpoints/phase3/<RunLabel>`.

## Step 7 — Run Phase 3 tests

These unit tests do not need PySpark installed on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_phase3_event_validation.py -q
```

## Step 8 — Record and push Phase 3

Review these files:
- `docs/project/phase3_scope.md`
- `docs/project/phase3_run_summary_template.md`
- `results/phase3/<RunLabel>_summary.json` (machine-generated local evidence; ignored by Git)

Copy measured values from the summary JSON into a new tracked summary:

```powershell
Copy-Item .\docs\project\phase3_run_summary_template.md .\docs\project\phase3_run_summary.md
notepad .\docs\project\phase3_run_summary.md
```

Do not claim Phase 3 passed until the Spark job succeeds and HDFS contains the Parquet output and checkpoints. Then stage only intended files:

```powershell
git add README_PHASE3.md
git add docker/phase3/compose.yaml
git add scripts/spark scripts/phase3
 git add tests/test_phase3_event_validation.py
git add docs/project/phase3_scope.md docs/project/phase3_run_summary_template.md docs/project/phase3_run_summary.md
git diff --cached --stat
git status --short
git commit -m "phase-3: add Spark Structured Streaming and HDFS pipeline"
git push origin main
```

If the local run summary JSON is mounted and you want to preserve its schema/tracking metadata, don't stage `results` wholesale: keep generated files ignored and summarize the relevant counts in `docs/project/phase3_run_summary.md`.

After phase exit criteria pass, tag it:

```powershell
git tag -a phase-3-complete -m "Spark Structured Streaming and HDFS output verified"
git push origin phase-3-complete
```

## Important limits

This first Phase 3 run proves end-to-end Kafka → Spark Structured Streaming → HDFS/Parquet and checkpointing on a single-worker local Docker cluster. It is not yet the Phase 7 load/scalability study, multi-worker speedup benchmark, fault-recovery experiment, or final production deployment.
