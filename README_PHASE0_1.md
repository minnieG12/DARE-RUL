# DARE-RUL — Phase 0 and Phase 1 Starter Bundle

This bundle is prepared for the existing project folder:

`E:\Projects\big data\DARE-RUL`

It does **not** delete or move your existing `data` or `docs` folders.
It uses the extracted dataset directory `data\CMAPSSData`. Your ZIP copy of the dataset can stay as a backup; do not extract it again unless validation reports missing files.

## What the phases mean

- **Phase 0 — Get the workshop ready:** check tools, create the project folders, prepare Python packages and initialize Git. Git will track our code but ignore the existing study documents and raw dataset.
- **Phase 1 — Check the ingredients and research plan:** validate all four C-MAPSS subsets, create data checksums, and record the baseline/research questions we must answer before building Kafka and Spark.

## Before starting

1. Make sure Docker Desktop is open. Some checks can still be recorded as unavailable if Docker is not running.
2. Keep the project folder exactly at `E:\Projects\big data\DARE-RUL`.
3. In File Explorer, the dataset folder should be `DARE-RUL\data\CMAPSSData` and contain `train_FD001.txt` through `train_FD004.txt`, `test_FD001.txt` through `test_FD004.txt`, and `RUL_FD001.txt` through `RUL_FD004.txt`. Windows may hide `.txt` extensions.
4. Do not delete or rename `data\CMAPSSData` or the existing `docs` folder.

## Install the bundle into the project

Download `DARE_RUL_Phase0_1_Code.zip`, then open PowerShell and run:

```powershell
$Project = 'E:\Projects\big data\DARE-RUL'
$Zip = Join-Path $env:USERPROFILE 'Downloads\DARE_RUL_Phase0_1_Code.zip'
Test-Path -LiteralPath $Project
Test-Path -LiteralPath $Zip
```

Both should return `True`. If your browser saved the ZIP somewhere else, update `$Zip` to the actual path. Then extract into the project:

```powershell
Expand-Archive -LiteralPath $Zip -DestinationPath $Project
Set-Location $Project
```

If PowerShell says a file already exists, stop and read the message instead of forcing an overwrite. The bundle is designed to add new setup files while leaving the existing data and study documents alone.

If PowerShell blocks the scripts, allow scripts only in the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This is temporary; it does not change the machine-wide policy.

## Phase 0 — exact commands

### 0.1 Create the standard folders

```powershell
.\scripts\setup\phase0_initialize_structure.ps1
```

This makes missing folders such as `src`, `tests`, `scripts\kafka`, `scripts\spark`, `results\phase1`, `docker` and `paper`. It does not erase anything.

### 0.2 Check the software and dataset location

```powershell
.\scripts\setup\phase0_check_environment.ps1
```

Read the screen output and the saved report:

```powershell
notepad .\results\phase0\environment_report.txt
```

Expected tools include Python 3.10, Git, Docker Desktop/Compose, WSL2 and Java. Docker's server check requires Docker Desktop's engine to be running. Do not install random Spark/PySpark versions yet; we'll pin compatible versions when we implement Phase 3.

### 0.3 Create the Python environment

First check Python 3.10:

```powershell
py -3.10 --version
```

If it prints Python 3.10.x, create the virtual environment:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements-base.txt
.\.venv\Scripts\python.exe -m pip freeze | Set-Content -Encoding utf8 .\requirements-lock.txt
```

Using `.venv\Scripts\python.exe` directly avoids needing to activate the environment. A virtual environment is a separate toolbox for this project, so packages for other projects are not changed.

If `py -3.10 --version` fails, stop and share the output before continuing.

### 0.4 Set up Git safely

Check whether Git is available:

```powershell
git --version
```

Initialize the repository only if it is not already a repository:

```powershell
if (-not (Test-Path .git)) { git init }
git status --short --ignored
```

The root `.gitignore` ignores the existing `docs` study materials except for the new `docs\project` folder, and ignores the raw `data\CMAPSSData` files. This prevents study documents and dataset files from being accidentally uploaded to GitHub. The files remain on your computer.

Check that a sample raw file is ignored (the exact filename must exist):

```powershell
git check-ignore -v .\data\CMAPSSData\train_FD001.txt
```

Check the generated project checklist is **not** ignored:

```powershell
git check-ignore -v .\docs\project\phase1_checklist.md
```

For the second command, no output and a non-zero exit code means the file is not ignored; that is expected. Review what will be tracked before the first commit:

```powershell
git add .gitignore README.md requirements-base.txt requirements-lock.txt scripts docs/project
 git status --short
```

If `requirements-lock.txt` was not created yet, omit it from that `git add` command. Do not run `git add data` or `git add -f` for the raw dataset. Only commit after reviewing the staged list:

```powershell
git commit -m "Set up DARE-RUL Phase 0 and Phase 1"
```

If Git asks for your identity, configure your Git name/email as instructed by Git; do not put passwords or tokens in the repository.

## Phase 1 — validate the dataset

Run this only after the Python dependencies are installed:

```powershell
.\.venv\Scripts\python.exe .\scripts\setup\phase1_validate_cmapss.py
```

Expected: `PASS` for `FD001`, `FD002`, `FD003` and `FD004`. The checker verifies that all 12 files exist, train/test rows have 26 columns, values are numeric and non-missing, engine-cycle pairs are unique, cycles increase within each engine, training RUL reaches zero at each engine's final observed cycle, and each test RUL file has one target per test engine.

The report and checksum manifest are saved under `results\phase1`:

- `cmapss_validation.txt` — what was checked and its result.
- `raw_data_sha256.csv` — fingerprints of the files under `data\CMAPSSData`; these help detect unintended file changes later.

A PASS is an initial structural validation; it does not prove every possible data issue is absent. Do not train models before resolving any failed check.

## Phase 1 — research notes

Use `docs\project\phase1_checklist.md`, `docs\project\literature\literature_matrix_template.csv` and `docs\project\research_log.md` to record what is complete and what remains.

Our proposed direction is a multi-resolution ensemble (15-cycle and 30-cycle feature experts) with adaptive weighting informed by validation-based model reliability and prediction disagreement. This is a **hypothesis to test**, not a guaranteed improvement or proven novelty. The literature review must establish the closest prior work, the baseline method and the evaluation protocol. Never use held-out test labels to train the adaptive weights.

## Do not do yet

- Do not install PySpark 4.x alongside Java 11.
- Do not start Phase 2 until Phase 0/1 checks are understood and the data validation passes.
- Do not upload raw C-MAPSS data or private study documents to a public Git repository.
- Do not delete the existing `docs` or `data` folders.
