# DARE-RUL Phase 3 — Spark Ivy Cache Fix

## Error addressed

Spark's dependency resolver failed while writing a file under `/home/spark/.ivy2/cache`:

`FileNotFoundException: ... resolved-org.apache.spark-...xml (No such file or directory)`

The failure occurs during Maven/Ivy dependency resolution, before `kafka_to_hdfs.py` starts. It is not caused by Kafka message contents or HDFS output.

## Fix

The Spark job service uses `scripts/spark/spark_job_entrypoint.sh`, which creates a writable `/tmp/dare-rul-ivy/cache` directory and launches `spark-submit` with `spark.jars.ivy` set to `/tmp/dare-rul-ivy`.

## Apply

Extract this ZIP at the repository root, `E:\Projects\big data\DARE-RUL`, replacing the single file `docker/phase3/compose.yaml` and adding `scripts/spark/spark_job_entrypoint.sh`.

Then run:

```powershell
docker compose -f .\docker\phase3\compose.yaml config
git diff -- .\docker\phase3\compose.yaml
```

Use a new run label after the fix. Do not delete Kafka volumes or HDFS checkpoints to address this Ivy-resolution error.
