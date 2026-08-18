# Databricks CLI Setup

## What is the Databricks CLI?

The Databricks CLI is a command-line tool for interacting with a Databricks workspace from your local machine. It supports operations such as copying files to Unity Catalog volumes, managing jobs and clusters, and running workspace commands without using the Databricks UI. For this medallion pipeline project, the CLI is the bridge between locally generated sample CSVs in `data/` and the Databricks environment where Bronze ingestion notebooks or jobs read those files.

## Why use the CLI instead of manual uploads?

Manual uploads through the Databricks UI work for one-off tests, but they are easy to forget, hard to reproduce, and do not version well in project documentation. The sample data generator in `src/data_generation/` can be re-run at any time (for example, after changing seed or injected quality defects). With the CLI, the same documented sync command re-uploads the refreshed files to a fixed volume or DBFS path so Bronze ingestion always sees the current dataset. That repeatability keeps local generation, upload, and pipeline runs aligned for development and assessment.

## Pip CLI vs official standalone CLI

This project initially used the legacy **`databricks-cli`** pip package (v0.18.x). That package is deprecated. We switched to the **official standalone Databricks CLI** (v0.205+ / v1.x) because Unity Catalog workflows require commands that the old pip CLI does not support, including:

- `databricks catalogs`
- `databricks schemas`
- `databricks volumes`

The new CLI is required for uploading sample CSVs to Unity Catalog volumes and for managing catalog objects as part of this pipeline.

## Install and verify (Windows)

### 1. Remove the deprecated pip package

```powershell
pip uninstall databricks-cli -y
```

### 2. Install the official standalone CLI

On Windows, Databricks documents **WinGet** as the primary install method (there is no `install.ps1` script in the [setup-cli](https://github.com/databricks/setup-cli) repository; only `install.sh` is provided for curl-based installs, typically via WSL on Windows):

```powershell
winget install Databricks.DatabricksCLI --accept-package-agreements --accept-source-agreements
```

> **Note:** Some guides reference `irm https://raw.githubusercontent.com/databricks/setup-cli/main/install.ps1 | iex`. That URL currently returns 404; use WinGet (above) or Chocolatey (`choco install databricks-cli`) on Windows instead.

### 3. Restart your terminal

WinGet updates the system `PATH`. **Close and reopen your terminal** (or open a new PowerShell window) before verifying the install. Without a restart, `databricks` may still resolve to the old pip shim or not be found.

### 4. Verify the installation

```powershell
databricks -v
```

On this machine, after uninstalling pip `databricks-cli` and installing via WinGet, verification succeeded with:

```
Databricks CLI v1.12.1
```

## Unity Catalog landing zone (completed)

Sample CSVs are stored in a Unity Catalog volume for Bronze ingestion.

| Object | Full name |
|--------|-----------|
| Catalog | `workspace` |
| Schema | `workspace.raw_landing` |
| Volume | `workspace.raw_landing.landing_zone` |
| Volume path | `/Volumes/workspace/raw_landing/landing_zone/` |

### Uploaded files

| File | Size | Volume path |
|------|------|-------------|
| `customers.csv` | 715 KB | `/Volumes/workspace/raw_landing/landing_zone/customers.csv` |
| `orders.csv` | 5.82 MB | `/Volumes/workspace/raw_landing/landing_zone/orders.csv` |
| `products.csv` | 34.2 KB | `/Volumes/workspace/raw_landing/landing_zone/products.csv` |

### Commands used

Run from the project root after `databricks auth login` (or with a configured profile). Create the schema and volume once, then re-run the `fs cp` commands whenever sample data is regenerated locally.

```powershell
databricks schemas create raw_landing workspace

databricks volumes create landing_zone workspace.raw_landing --volume-type MANAGED

databricks fs cp data/customers.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/customers.csv
databricks fs cp data/orders.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/orders.csv
databricks fs cp data/products.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/products.csv
```

Bronze notebooks and jobs should read from `/Volumes/workspace/raw_landing/landing_zone/` (or the equivalent `dbfs:/Volumes/...` path).

