#!/usr/bin/env bash
set -euo pipefail

# Spark's package resolver writes resolved-*.xml under the Ivy cache.
# Some Spark image/container runs do not have the default ~/.ivy2/cache
# directory available. Use a writable, ephemeral directory and create the
# cache tree before spark-submit resolves --packages.
IVY_USER_DIR="${SPARK_IVY_DIR:-/tmp/dare-rul-ivy}"
mkdir -p "${IVY_USER_DIR}/cache" "${IVY_USER_DIR}/jars"

echo "Using writable Spark Ivy directory: ${IVY_USER_DIR}"
exec /opt/spark/bin/spark-submit --conf "spark.jars.ivy=${IVY_USER_DIR}" "$@"
