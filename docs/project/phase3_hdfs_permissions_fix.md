# Phase 3 HDFS Permission Fix

The initial permission script used Hadoop subcommands without their required leading dash (`mkdir`, `chown`, `chmod`, `ls`). The `hdfs dfs` CLI expects `-mkdir`, `-chown`, `-chmod`, and `-ls`.

Run from the project root in PowerShell:

```powershell
.\scripts\phase3\prepare_hdfs_permissions.ps1
```

The script creates `/dare-rul`, `/dare-rul/phase3`, and `/dare-rul/checkpoints/phase3`, assigns those project directories to the Spark job user, and verifies their ownership. It does not change permissions on `/` and does not delete any HDFS paths or volumes.

Expected final output includes a directory listing for all four paths and:

`SUCCESS: HDFS project directories are prepared for the Spark user.`

If `-chown` fails with an authorization error, stop and inspect the NameNode container's effective user and HDFS superuser configuration rather than broadening permissions recursively.
