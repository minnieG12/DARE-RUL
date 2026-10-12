# Phase 3 Troubleshooting Record

This is the single retained troubleshooting note for Phase 3. The individual Ivy/HDFS-fix README files were merged here.

## 1. Spark Ivy cache

**Symptom:** `FileNotFoundException` under `/home/spark/.ivy2/cache/resolved-...xml` before the Spark app starts.

**Cause:** Ivy tried to write dependency-resolution files into a cache path that was not writable in the job container.

**Resolution:** `scripts/spark/spark_job_entrypoint.sh` creates and uses `/tmp/dare-rul-ivy`. The connector jars downloaded successfully after this change.

## 2. HDFS path permissions

**Symptom:** `AccessControlException: Permission denied: user=spark, access=WRITE, inode="/"`.

**Cause:** The Spark job user could not create the project path under HDFS root.

**Resolution:** Run `scripts/phase3/prepare_hdfs_permissions.ps1`. It uses Hadoop CLI commands with leading dashes (`-mkdir`, `-chown`, `-chmod`, `-ls`) and gives the Spark user ownership of the project-specific directories. It does not change permissions on `/`.

## 3. Interpreting Spark warnings

The successful run logged the optional native Hadoop library warning, that AQE is disabled for streaming, and Kafka AdminClient option warnings. The job still completed and reported `PASS`. These warnings should be revisited if they become errors or if the runtime environment changes.

## 4. Data interpretation

The Spark summary counts rows by reading the Parquet sinks back. In the recorded run, it found 500 valid rows and 0 invalid rows. The existence of small Parquet files under the invalid output directory alone does not mean invalid records were written; use the read-back row count.
