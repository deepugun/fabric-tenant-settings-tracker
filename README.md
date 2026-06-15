# Fabric Tenant Settings Change Tracker

A lightweight, automated solution that detects **daily changes** to Microsoft Fabric tenant settings and sends **email alerts** with detailed diffs. Built entirely with Fabric-native tools: Spark SQL notebooks + Data Pipelines + Outlook activity.

## What It Does

Runs daily to answer three questions:

1. **What's new?** — Settings Microsoft released to your tenant since yesterday
2. **What's gone?** — Settings that were removed or deprecated
3. **What changed?** — Settings where `enabled`, `security groups`, `properties`, or any other field was modified — showing the **old value → new value**

All changes are stored in a Delta audit table for historical tracking, and an HTML email alert is sent via the pipeline's Outlook activity.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Tenant_Settings_Alert_Pipeline (scheduled daily)    │
│                                                       │
│  ┌─────────────────────────┐                          │
│  │ Run_Settings_Tracker    │  Notebook (Spark SQL)    │
│  │ • Fetch Admin API       │                          │
│  │ • MERGE INTO snapshot   │                          │
│  │ • EXCEPT for new/removed│                          │
│  │ • JOIN for changed      │                          │
│  │ • INSERT INTO audit log │                          │
│  │ • Exit with JSON payload│                          │
│  └────────┬────────────────┘                          │
│           │                                           │
│  ┌────────▼────────────────┐                          │
│  │ Check_For_Changes       │  IfCondition             │
│  │ has_changes == true?    │                          │
│  └────────┬────────────────┘                          │
│           │ Yes                                       │
│  ┌────────▼────────────────┐                          │
│  │ Send_Change_Alert_Email │  Office 365 Outlook      │
│  │ subject + HTML body     │  (configured in UI)      │
│  └─────────────────────────┘                          │
└──────────────────────────────────────────────────────┘
```

## Delta Tables

| Table | Purpose |
|-------|---------|
| `tenant_settings_snapshots` | Daily snapshot of all tenant settings (partitioned by `snapshot_date`) |
| `tenant_settings_changes` | Audit log — one row per change with `change_type`, `field_changed`, `old_value`, `new_value` |

## Email Alert Sample

The HTML email includes color-coded tables:

- **Green header** — New settings (with enabled/disabled state)
- **Red header** — Removed settings
- **Orange header** — Changed settings with old → new values per field

## Prerequisites

- Microsoft Fabric workspace with a **lakehouse** attached
- **Fabric Admin** privileges (to call `GET /v1/admin/tenantsettings`)
- **Office 365 Outlook** connection in the pipeline (for email alerts)
- Fabric capacity (Premium or Fabric trial)

## Deployment

### Option 1: Use the pre-built notebook and pipeline

1. Import `Tenant_Settings_Change_Tracker.ipynb` into your Fabric workspace
2. Attach a lakehouse to the notebook
3. Create a Data Pipeline with:
   - **TridentNotebook** activity pointing to the notebook
   - **IfCondition** checking `@json(activity('Run_Settings_Tracker').output.result.exitValue).has_changes`
   - **Office365Email** activity in the True branch with:
     - **To**: your email
     - **Subject**: `@json(activity('Run_Settings_Tracker').output.result.exitValue).subject`
     - **Body**: `@json(activity('Run_Settings_Tracker').output.result.exitValue).body_html`
4. Schedule the pipeline to run daily

### Option 2: Deploy via Fabric REST API

See [docs/deployment.md](docs/deployment.md) for step-by-step API commands.

## Usage

### First run
Creates the baseline snapshot. No comparisons or emails are sent.

### Second run onward
Compares today's settings against yesterday's and:
- Prints new / removed / changed settings in the notebook output
- Logs all changes to the `tenant_settings_changes` Delta table
- Exits with a JSON payload containing the email subject + HTML body
- The pipeline's IfCondition routes to the Outlook activity if changes exist

### Querying the audit log

```sql
-- All changes in the last 7 days
SELECT * FROM tenant_settings_changes
WHERE change_date >= date_sub(current_date(), 7)
ORDER BY change_date DESC, change_type, setting_name

-- Settings that were toggled on/off
SELECT setting_name, change_date, old_value, new_value
FROM tenant_settings_changes
WHERE field_changed = 'enabled'
ORDER BY change_date DESC
```

## How Is This Different from FUAM?

| Aspect | FUAM | This Solution |
|--------|------|---------------|
| **Scope** | Holistic monitoring: tenant settings, activities, workspaces, capacities, CU metrics, scanner metadata, git connections, refreshables | **Tenant settings only** |
| **Tenant settings approach** | Stores a point-in-time snapshot for reporting dashboards | **Daily diff**: detects new, removed, and changed settings with field-level old → new values |
| **Change detection** | No built-in day-over-day diff or change alerting for settings | **Core purpose** — SQL EXCEPT + JOIN to find exactly what changed |
| **Alerting** | No email alerts for setting changes | **Pipeline-based Outlook email** with color-coded HTML report |
| **Audit trail** | Settings stored in lakehouse but no dedicated change log | **Dedicated `tenant_settings_changes` Delta table** — one row per changed field |
| **Size** | Large solution accelerator (20+ notebooks, pipelines, reports, semantic models) | **1 notebook + 1 pipeline + 2 Delta tables** |
| **Setup time** | Multi-step deployment with configuration | < 10 minutes |
| **Use case** | "How is my Fabric estate configured and used?" | "What tenant settings changed today and what were the old/new values?" |
| **Complementary?** | Yes — FUAM provides the broad view | Yes — this provides the targeted change alerting FUAM doesn't do |

**TL;DR**: FUAM is a broad monitoring dashboard. This is a focused change-detection + alerting tool. They complement each other — use FUAM for the big picture, use this to get notified the moment a setting changes.

## Project Structure

```
├── Tenant_Settings_Change_Tracker.ipynb   # Spark SQL notebook
├── pipeline-content.json                   # Pipeline definition (JSON)
├── docs/
│   └── deployment.md                       # REST API deployment guide
├── README.md
├── LICENSE
└── .gitignore
```

## License

MIT License — see [LICENSE](LICENSE).
