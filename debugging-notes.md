# Debugging Notes

Real issues encountered while building and running the medallion pipeline, with root causes and fixes.

---

## Bronze ingest: `input_file_name()` blocked under Unity Catalog

**Issue**

Running `src/bronze/01_ingest_customers.py` on Databricks failed with:

```
[UC_COMMAND_NOT_SUPPORTED.WITH_RECOMMENDATION] The command(s): input_file_name are not
supported in Unity Catalog. Please use _metadata.file_path instead. SQLSTATE: 0AKUC
```

**Root Cause**

`input_file_name()` is a legacy Spark function for recording the source file path at read time. Unity Catalog disallows it on Volume-based paths for governance and security reasons—it behaved differently on raw DBFS paths and is not considered safe for UC-managed storage.

**Fix**

In `add_ingest_metadata()` inside `src/bronze/01_ingest_customers.py`, replaced:

```python
input_file_name().alias("_source_file")
```

with the Unity Catalog–safe file metadata column:

```python
col("_metadata.file_path").alias("_source_file")
```

Removed the unused `input_file_name` import. Re-run the Bronze customers ingest after this change.

---

## Silver completeness: `__file__` undefined in Databricks notebooks

**Issue**

Running the Silver completeness check on Databricks failed with:

```
NameError: name '__file__' is not defined
```

**Root Cause**

`src/silver/run_01_quality_completeness_databricks.py` used `Path(__file__).resolve().parent` to locate `01_quality_completeness.py` for dynamic import. Databricks notebooks and some `%run` contexts execute code interactively without defining `__file__`, so path resolution that works under `python script.py` locally fails on the cluster.

**Fix**

Moved verification logic (`verify_expected_failures`, `verify_with_sql`, `run_with_verification`) into `src/silver/01_quality_completeness.py` so the main module is a single Databricks-safe entry point. Rewrote the runner to use `runpy.run_path("src/silver/01_quality_completeness.py", run_name="__main__")` with a repo-relative path constant—no `__file__` or `importlib` path discovery.

On Databricks, run either:

```python
%run ./src/silver/01_quality_completeness
```

or:

```python
%run ./src/silver/run_01_quality_completeness_databricks
```

Both execute from the repo root working directory.

---

## Silver completeness: `runpy` runner file not in Databricks Workspace

**Issue**

Running `run_01_quality_completeness_databricks.py` on Databricks failed with:

```
FileNotFoundError: [Errno 2] No such file or directory:
'/Workspace/Users/kalpana.jain@tothenew.com/src/silver/01_quality_completeness.py'
```

**Root Cause**

The runner used `runpy.run_path("src/silver/01_quality_completeness.py")` to load logic from a sibling file at runtime. That path exists in the local git repo but was never uploaded to the Databricks Workspace—only the pasted runner cell exists there. Splitting logic across two files that must both be manually synced is fragile.

**Fix**

Regenerated `run_01_quality_completeness_databricks.py` as a **fully self-contained** script with all completeness-check logic inlined. No `runpy`, no dynamic file loading, no dependency on other repo files. Paste this single file into one Databricks notebook cell. The modular `01_quality_completeness.py` remains in git for local development.

Added a `.cursorrules` rule: Databricks notebook runners must always follow this self-contained pattern.

