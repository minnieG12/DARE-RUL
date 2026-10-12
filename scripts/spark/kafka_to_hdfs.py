"""Read a finite Kafka telemetry topic with Spark Structured Streaming and write Parquet to HDFS."""
from __future__ import annotations
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, DoubleType
from pyspark.sql.window import Window

SPARK_VERSION = "3.5.1"
KAFKA_CONNECTOR = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"


def event_schema() -> StructType:
    fields = [
        StructField("schema_version", IntegerType(), True),
        StructField("dataset", StringType(), True),
        StructField("split", StringType(), True),
        StructField("engine_id", LongType(), True),
        StructField("cycle", LongType(), True),
        StructField("setting_1", DoubleType(), True),
        StructField("setting_2", DoubleType(), True),
        StructField("setting_3", DoubleType(), True),
    ]
    fields.extend(StructField(f"sensor_{i}", DoubleType(), True) for i in range(1, 22))
    return StructType(fields)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, help="Use a unique, clean Phase 2 test topic")
    parser.add_argument("--run-label", required=True, help="Unique letters/numbers/dashes/underscores label")
    parser.add_argument("--expected-messages", type=int, default=500)
    parser.add_argument("--max-offsets-per-trigger", type=int, default=200)
    parser.add_argument("--bootstrap-servers", default="kafka:9093")
    parser.add_argument("--hdfs-uri", default="hdfs://namenode:9000")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", args.run_label):
        parser.error("--run-label must contain only letters, numbers, dot, underscore or dash and start with a letter/number")
    if args.expected_messages < 0:
        parser.error("--expected-messages must be >= 0")
    if args.max_offsets_per_trigger < 1:
        parser.error("--max-offsets-per-trigger must be >= 1")
    if not args.topic or "," in args.topic:
        parser.error("--topic must be one non-empty Kafka topic")
    return args


def hdfs_exists(spark: SparkSession, uri: str) -> bool:
    jvm = spark._jvm
    conf = spark.sparkContext._jsc.hadoopConfiguration()
    path = jvm.org.apache.hadoop.fs.Path(uri)
    fs = path.getFileSystem(conf)
    return bool(fs.exists(path))


def parquet_file_count(spark: SparkSession, uri: str) -> int:
    jvm = spark._jvm
    conf = spark.sparkContext._jsc.hadoopConfiguration()
    path = jvm.org.apache.hadoop.fs.Path(uri)
    fs = path.getFileSystem(conf)
    if not fs.exists(path):
        return 0
    statuses = fs.globStatus(jvm.org.apache.hadoop.fs.Path(uri.rstrip("/") + "/part-*.parquet"))
    return 0 if statuses is None else int(len(statuses))


def count_parquet_rows(spark: SparkSession, uri: str) -> int:
    if parquet_file_count(spark, uri) == 0:
        return 0
    return int(spark.read.parquet(uri).count())


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    hdfs_base = args.hdfs_uri.rstrip("/")
    run_root = f"{hdfs_base}/dare-rul/phase3/{args.run_label}"
    valid_path = f"{run_root}/parquet"
    invalid_path = f"{run_root}/invalid"
    checkpoint_root = f"{hdfs_base}/dare-rul/checkpoints/phase3/{args.run_label}"
    valid_checkpoint = f"{checkpoint_root}/valid"
    invalid_checkpoint = f"{checkpoint_root}/invalid"

    spark = (
        SparkSession.builder
        .appName(f"DARE-RUL-Phase3-{args.run_label}")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.hadoop.fs.defaultFS", hdfs_base)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        for path in [run_root, checkpoint_root]:
            if hdfs_exists(spark, path):
                raise FileExistsError(
                    f"HDFS path already exists: {path}. Choose a new --run-label; do not delete checkpoints blindly."
                )

        schema = event_schema()
        kafka = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", args.bootstrap_servers)
            .option("subscribe", args.topic)
            .option("startingOffsets", "earliest")
            .option("failOnDataLoss", "true")
            .option("maxOffsetsPerTrigger", str(args.max_offsets_per_trigger))
            .load()
        )
        parsed = (
            kafka.select(
                F.col("key").cast("string").alias("kafka_key"),
                F.col("topic").alias("kafka_topic"),
                F.col("partition").alias("kafka_partition"),
                F.col("offset").alias("kafka_offset"),
                F.col("timestamp").alias("kafka_timestamp"),
                F.col("value").cast("string").alias("json_value"),
            )
            .withColumn("event", F.from_json(F.col("json_value"), schema))
        )

        required = (
            F.col("event").isNotNull()
            & F.col("event.schema_version").eqNullSafe(1)
            & F.col("event.dataset").isin("FD001", "FD002", "FD003", "FD004")
            & F.col("event.split").isin("train", "test")
            & (F.col("event.engine_id") > 0)
            & (F.col("event.cycle") > 0)
        )
        numeric_fields = ["setting_1", "setting_2", "setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
        for field in numeric_fields:
            required = required & F.col(f"event.{field}").isNotNull() & (~F.isnan(F.col(f"event.{field}")))
        leaked_target = F.lower(F.col("json_value")).rlike(r'"\s*(rul|remaining_useful_life|target|label|y)\s*"\s*:')
        valid_condition = required & (~leaked_target)

        valid = parsed.filter(valid_condition).select(
            "kafka_key", "kafka_topic", "kafka_partition", "kafka_offset", "kafka_timestamp", "event.*"
        )
        invalid = parsed.filter(~valid_condition).select(
            "kafka_key", "kafka_topic", "kafka_partition", "kafka_offset", "kafka_timestamp", "json_value",
            F.when(leaked_target, F.lit("forbidden target/RUL field in payload"))
             .otherwise(F.lit("malformed JSON or missing/invalid telemetry field")).alias("validation_error")
        )

        query_valid = (
            valid.writeStream.format("parquet")
            .option("path", valid_path)
            .option("checkpointLocation", valid_checkpoint)
            .outputMode("append")
            .trigger(availableNow=True)
            .start()
        )
        query_invalid = (
            invalid.writeStream.format("parquet")
            .option("path", invalid_path)
            .option("checkpointLocation", invalid_checkpoint)
            .outputMode("append")
            .trigger(availableNow=True)
            .start()
        )
        query_valid.awaitTermination()
        query_invalid.awaitTermination()

        valid_rows = count_parquet_rows(spark, valid_path)
        invalid_rows = count_parquet_rows(spark, invalid_path)
        result = spark.read.parquet(valid_path) if valid_rows else None
        duplicates = 0
        order_warnings = 0
        if result is not None:
            duplicates = int(
                result.groupBy("dataset", "split", "engine_id", "cycle")
                .count().filter(F.col("count") > 1).count()
            )
            ordering = Window.partitionBy("kafka_key").orderBy("kafka_offset")
            ordered = result.withColumn("previous_cycle", F.lag("cycle").over(ordering))
            order_warnings = int(
                ordered.filter(F.col("previous_cycle").isNotNull() & (F.col("cycle") <= F.col("previous_cycle"))).count()
            )

        elapsed = time.perf_counter() - started
        status = "PASS"
        if invalid_rows != 0 or duplicates != 0 or order_warnings != 0:
            status = "FAIL_DATA_QUALITY"
        if args.expected_messages and valid_rows + invalid_rows != args.expected_messages:
            status = "FAIL_COUNT_MISMATCH"

        summary = {
            "project": "DARE-RUL",
            "phase": 3,
            "run_label": args.run_label,
            "spark_version": spark.version,
            "topic": args.topic,
            "expected_messages": args.expected_messages,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows,
            "duplicate_engine_cycle_pairs": duplicates,
            "cycle_order_warnings": order_warnings,
            "elapsed_seconds": round(elapsed, 2),
            "hdfs_parquet_path": valid_path,
            "hdfs_invalid_path": invalid_path,
            "hdfs_checkpoint_root": checkpoint_root,
            "status": status,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        }
        print("\nDARE-RUL Phase 3 Spark/HDFS summary")
        print(json.dumps(summary, indent=2))
        try:
            local_out = Path("/opt/host-results") / f"{args.run_label}_summary.json"
            local_out.parent.mkdir(parents=True, exist_ok=True)
            local_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"Host summary file: {local_out}")
        except Exception as exc:
            print(f"Note: host summary file could not be written from container: {exc}")
        return 0 if status == "PASS" else 2
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
