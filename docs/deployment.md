# Deployment via Fabric REST API

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed
- Logged in with `az login` (account with Fabric Admin privileges)
- Target workspace ID (replace `<WORKSPACE_ID>` below)

## Step 1: Create the Notebook

```bash
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<WORKSPACE_ID>/items" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"displayName": "Tenant_Settings_Change_Tracker", "type": "Notebook", "description": "Tracks Fabric tenant settings changes daily"}'
```

Save the returned `id` as `<NOTEBOOK_ID>`.

## Step 2: Upload Notebook Content

```powershell
# Base64 encode the notebook
$content = Get-Content "Tenant_Settings_Change_Tracker.ipynb" -Raw
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($content))

# Build the payload
$body = @{
  definition = @{
    format = "ipynb"
    parts = @(@{
      path = "notebook-content.ipynb"
      payload = $b64
      payloadType = "InlineBase64"
    })
  }
} | ConvertTo-Json -Depth 5 -Compress

$body | Out-File "payload.json" -Encoding utf8

# Push to Fabric
az rest --method POST `
  --url "https://api.fabric.microsoft.com/v1/workspaces/<WORKSPACE_ID>/items/<NOTEBOOK_ID>/updateDefinition" `
  --resource "https://api.fabric.microsoft.com" `
  --body "@payload.json"
```

## Step 3: Create the Pipeline

```bash
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<WORKSPACE_ID>/items" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"displayName": "Tenant_Settings_Alert_Pipeline", "type": "DataPipeline", "description": "Runs tenant settings tracker and sends Outlook email"}'
```

Save the returned `id` as `<PIPELINE_ID>`.

## Step 4: Upload Pipeline Definition

Update `<NOTEBOOK_ID>` and `<WORKSPACE_ID>` in `pipeline-content.json`, then:

```powershell
$content = Get-Content "pipeline-content.json" -Raw
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($content))

$body = @{
  definition = @{
    parts = @(@{
      path = "pipeline-content.json"
      payload = $b64
      payloadType = "InlineBase64"
    })
  }
} | ConvertTo-Json -Depth 5 -Compress

$body | Out-File "pl_payload.json" -Encoding utf8

az rest --method POST `
  --url "https://api.fabric.microsoft.com/v1/workspaces/<WORKSPACE_ID>/items/<PIPELINE_ID>/updateDefinition" `
  --resource "https://api.fabric.microsoft.com" `
  --body "@pl_payload.json"
```

## Step 5: Add Outlook Activity (Fabric Portal)

The Office 365 Outlook connection requires an interactive OAuth sign-in that can only be done in the UI:

1. Open the pipeline in the Fabric portal
2. Open the **Check_For_Changes** IfCondition → **True** branch
3. Add an **Office 365 Outlook** activity
4. Configure:
   - **To**: your email address
   - **Subject**: `@json(activity('Run_Settings_Tracker').output.result.exitValue).subject`
   - **Body**: `@json(activity('Run_Settings_Tracker').output.result.exitValue).body_html`
   - **Importance**: High
5. Sign in when prompted

## Step 6: Attach Lakehouse & Schedule

1. Open the notebook → attach a lakehouse
2. Open the pipeline → Schedule → set to run daily
