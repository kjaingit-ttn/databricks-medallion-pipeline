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
