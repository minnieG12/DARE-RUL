# DARE-RUL Phase 3 — HDFS Permission Fix (v2)

This patch corrects the Hadoop CLI syntax in `scripts/phase3/prepare_hdfs_permissions.ps1` by adding the required dash to `-mkdir`, `-chown`, `-chmod`, and `-ls`.

Extract this ZIP into the existing `E:\Projects\big data\DARE-RUL` project root with overwrite enabled. It contains only the corrected permission script and its documentation.

Then run:

```powershell
.\scripts\phase3\prepare_hdfs_permissions.ps1
```

Do not delete Docker volumes or change permissions on HDFS `/`. If an authorization error persists after the syntax fix, preserve the output and troubleshoot the NameNode effective identity.
