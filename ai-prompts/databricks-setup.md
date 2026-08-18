# AI Prompt History — Databricks Setup

Log of prompts sent to Cursor and summaries of AI responses for Databricks environment setup.

---

## Prompt: Install and document Databricks CLI

**PROMPT SENT:** Check if the Databricks CLI is installed by running "databricks --version" in the terminal. If it's not found, install it via pip: pip install databricks-cli. Then verify the install by running "databricks --version" again.

Create database/DATABRICKS_CLI_SETUP.md explaining what the Databricks CLI is, why we're using it instead of manual file uploads (repeatability - any time the sample data is regenerated, the same CLI command re-syncs it to Databricks), and the exact commands used to install/verify it.

Then create ai-prompts/databricks-setup.md (if it doesn't exist) and log this prompt and your actions in it, following the same format used in ai-prompts/documentation.md and ai-prompts/data-generation.md.

**AI RESPONSE SUMMARY:** Ran `databricks --version`; the CLI was not installed (`databricks` not recognized). Installed via `pip install databricks-cli` (version 0.18.0). Re-ran `databricks --version` and confirmed `Version 0.18.0`. Created `database/DATABRICKS_CLI_SETUP.md` covering what the CLI is, why CLI sync beats manual uploads for repeatable data refreshes, and the exact check/install/verify commands with the observed version output.

**KEY OUTCOMES:**

| Step | Result |
|------|--------|
| Initial `databricks --version` | Not found |
| `pip install databricks-cli` | Installed 0.18.0 |
| Post-install `databricks --version` | `Version 0.18.0` |
| Docs created | `database/DATABRICKS_CLI_SETUP.md`, `ai-prompts/databricks-setup.md` |

---

## Prompt: Migrate to official standalone Databricks CLI

**PROMPT SENT:** Uninstall the old databricks-cli pip package by running: pip uninstall databricks-cli -y

Then install the new official Databricks CLI for Windows by running this in PowerShell:
irm https://raw.githubusercontent.com/databricks/setup-cli/main/install.ps1 | iex

After installation, close and note that the terminal needs to be restarted for PATH changes to take effect. Update database/DATABRICKS_CLI_SETUP.md to reflect that we switched from the deprecated pip-based CLI to the new official standalone CLI, and why (Unity Catalog volume commands like 'catalogs', 'schemas', 'volumes' are only supported in the new CLI).

**AI RESPONSE SUMMARY:** Uninstalled pip `databricks-cli` (0.18.0). The requested `install.ps1` URL returned 404 (only `install.sh` exists in setup-cli); installed the official standalone CLI via WinGet (`Databricks.DatabricksCLI` v1.12.1). Verified with `databricks -v` after refreshing PATH. Updated `database/DATABRICKS_CLI_SETUP.md` to document the pip-to-standalone migration, Unity Catalog command rationale, WinGet install steps, terminal restart requirement, and the `install.ps1` caveat.

**FILES CREATED OR CHANGED:**

- `database/DATABRICKS_CLI_SETUP.md` — rewritten install section for official CLI
- `ai-prompts/databricks-setup.md` — appended this log entry

**KEY OUTCOMES:**

| Step | Result |
|------|--------|
| `pip uninstall databricks-cli -y` | Removed 0.18.0 |
| `install.ps1` via `irm ... \| iex` | 404 Not Found |
| `winget install Databricks.DatabricksCLI` | Installed v1.12.1 |
| `databricks -v` (after PATH refresh) | `Databricks CLI v1.12.1` |

---

## Prompt: Catalog setup and CSV upload complete

**PROMPT SENT:** The Databricks catalog setup and CSV upload is complete:
- Schema created: workspace.raw_landing
- Volume created: workspace.raw_landing.landing_zone
- All 3 CSVs uploaded successfully to /Volumes/workspace/raw_landing/landing_zone/
  (customers.csv 715KB, orders.csv 5.82MB, products.csv 34.2KB)

Update database/DATABRICKS_CLI_SETUP.md to document the final volume path used, and append a completion entry to ai-prompts/databricks-setup.md summarizing that the upload succeeded and listing the exact commands that were run (schemas create, volumes create, fs cp x3).

**AI RESPONSE SUMMARY:** Documented the completed Unity Catalog landing zone in `database/DATABRICKS_CLI_SETUP.md`: schema `workspace.raw_landing`, volume `workspace.raw_landing.landing_zone`, volume path `/Volumes/workspace/raw_landing/landing_zone/`, and uploaded file sizes. Replaced the placeholder “Next steps” section with the schema/volume creation and three `fs cp` sync commands for repeatable re-uploads after local data regeneration.

**FILES CREATED OR CHANGED:**

- `database/DATABRICKS_CLI_SETUP.md` — added Unity Catalog landing zone section
- `ai-prompts/databricks-setup.md` — appended this completion entry

**COMMANDS RUN:**

```powershell
databricks schemas create raw_landing workspace

databricks volumes create landing_zone workspace.raw_landing --volume-type MANAGED

databricks fs cp data/customers.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/customers.csv
databricks fs cp data/orders.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/orders.csv
databricks fs cp data/products.csv dbfs:/Volumes/workspace/raw_landing/landing_zone/products.csv
```

**UPLOAD RESULT:**

| File | Size | Status |
|------|------|--------|
| `customers.csv` | 715 KB | Uploaded |
| `orders.csv` | 5.82 MB | Uploaded |
| `products.csv` | 34.2 KB | Uploaded |
