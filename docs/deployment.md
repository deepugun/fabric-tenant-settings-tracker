# Deployment Guide (Fabric Portal UI)

Everything below is done in the **Fabric portal** — no CLI, no REST API, no code.

## Prerequisites

- A **Microsoft Fabric workspace** with an active capacity (Premium or Fabric trial)
- **Fabric Admin** privileges (to call the tenant settings API)
- A **lakehouse** in the workspace (or you'll create one below)

---

## Step 1: Create a Lakehouse

1. Open your workspace in the [Fabric portal](https://app.fabric.microsoft.com)
2. Click **+ New item** → select **Lakehouse**
3. Name it (e.g., `AdminMonitoring_LH`) → click **Create**

---

## Step 2: Import the Notebook

1. In your workspace, click **+ New item** → select **Import notebook**
2. Select the `Tenant_Settings_Change_Tracker.ipynb` file from this repo
3. Once imported, open the notebook
4. In the left panel, click **Lakehouses** → **Add** → select the lakehouse you created in Step 1
5. The notebook is now connected — the Delta tables will be created automatically on first run

---

## Step 3: Test the Notebook (Optional)

1. Open the notebook
2. Click **Run all** to execute all cells
3. This first run creates the baseline snapshot — you should see:
   - `Created 'tenant_settings_snapshots' with today's snapshot`
   - `First run -- snapshot saved. Run again tomorrow for comparisons.`
4. Verify the `tenant_settings_snapshots` table appears in your lakehouse

---

## Step 4: Create the Data Pipeline

1. Go back to your workspace
2. Click **+ New item** → select **Data pipeline**
3. Name it `Tenant_Settings_Alert_Pipeline`

---

## Step 5: Add the Notebook Activity

1. In the pipeline canvas, from the **Activities** toolbar, drag a **Notebook** activity onto the canvas
2. Name it `Run_Settings_Tracker`
3. In the **Settings** tab:
   - **Workspace**: select your workspace
   - **Notebook**: select `Tenant_Settings_Change_Tracker`
4. In the **General** tab:
   - Set **Timeout** to `02:00:00`
   - Set **Retry** to `1`

---

## Step 6: Add the If Condition Activity

1. From the **Activities** toolbar, drag an **If Condition** activity onto the canvas
2. Name it `Check_For_Changes`
3. Draw a **green arrow** (On Success) from `Run_Settings_Tracker` → `Check_For_Changes`
4. In the **Activities** tab of the If Condition, click the **Expression** box and enter:

   ```
   @json(activity('Run_Settings_Tracker').output.result.exitValue).has_changes
   ```

---

## Step 7: Add the Outlook Email Activity (True Branch)

1. Click the **pencil icon** next to the **True** case to open the True branch canvas
2. From the **Activities** toolbar, drag an **Office 365 Outlook** activity onto the canvas
3. Name it `Send_Change_Alert_Email`
4. You will be prompted to **sign in** — sign in with your Microsoft 365 account to create the Outlook connection
5. In the **Settings** tab, configure:

   | Field | Value |
   |-------|-------|
   | **To** | Your email address (e.g., `you@company.com`) |
   | **Subject** | `@json(activity('Run_Settings_Tracker').output.result.exitValue).subject` |
   | **Body** | `@json(activity('Run_Settings_Tracker').output.result.exitValue).body_html` |
   | **Is HTML** | ✅ Yes (check this box) |
   | **Importance** | High |

6. Click the **back arrow** to return to the main pipeline canvas

---

## Step 8: Add a "No Changes" Action (False Branch — Optional)

1. Click the **pencil icon** next to the **False** case
2. Drag a **Set Variable** activity onto the canvas
3. Name it `Log_No_Changes`
4. In the **Settings** tab:
   - **Variable type**: Pipeline return value
   - **Name**: `status`
   - **Value**: `No changes detected`
5. Click back to return to the main canvas

---

## Step 9: Validate and Save

1. Click **Validate** in the toolbar — ensure no errors
2. Click **Save**
3. (Optional) Click **Run** to test the full pipeline end-to-end

---

## Step 10: Schedule the Pipeline

1. In the pipeline, click **Schedule** (clock icon in the toolbar)
2. Configure:
   - **Recurrence**: Daily
   - **Time**: pick a time (e.g., 8:00 AM)
   - **Time zone**: your time zone
3. Toggle the schedule **On**
4. Click **Apply**

---

## What Happens on Each Run

| Run | Behavior |
|-----|----------|
| **First run** | Fetches all tenant settings, stores baseline snapshot. No email sent. |
| **Second run onward** | Compares today vs yesterday. If new, removed, or changed settings are found → sends HTML email with full details. Logs all changes to the `tenant_settings_changes` audit table. |

---

## Verifying It Works

1. **Check the lakehouse** — you should see two tables:
   - `tenant_settings_snapshots` — one row per setting per day
   - `tenant_settings_changes` — one row per change (after the second run)

2. **Check your email** — if any settings changed, you'll receive an HTML email with:
   - New settings table (green) showing enabled/disabled state
   - Removed settings table (red)
   - Changed settings table (orange) showing old → new values for each field

3. **Query the audit log** — open a new notebook or SQL endpoint and run:

   ```sql
   SELECT * FROM tenant_settings_changes ORDER BY change_date DESC
   ```
