# Phase 3 — Local HDFS replication profile

- Purpose: document the local Kafka/Spark/HDFS integration environment.
- DataNodes: 1.
- Default replication factor: 1.
- The previous inspection found existing files with replication target 3.
- This profile aligns local replica metadata with the single-DataNode setup.
- This validates local data integrity; it does not demonstrate redundancy or fault recovery.
- Record the verified under-replicated, missing and corrupt block counts below after the inspection.
