# Phase 3 — Local HDFS Replication Profile

- **Profile:** local development integration; one HDFS DataNode.
- **Default replication factor:** 1.
- **Action recorded:** existing `/dare-rul` file replication targets were aligned to the single-DataNode profile with `hdfs dfs -setrep -w 1 -R /dare-rul`.
- **Verification:** the subsequent `hdfs fsck /dare-rul -files -blocks` summary reported 0 under-replicated blocks, 0 missing blocks, 0 corrupt blocks, and `The filesystem under path '/dare-rul' is HEALTHY`.
- **Interpretation:** this establishes local HDFS file/block integrity for the one-DataNode configuration. It does **not** establish redundant storage, horizontal scaling, high availability or node-loss recovery.
- **Recheck command:** `docker exec dare-rul-namenode hdfs fsck /dare-rul -files -blocks`.
