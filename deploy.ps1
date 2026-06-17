<#
.SYNOPSIS
    Deploys (creates or updates) the Tenant Settings Alert Pipeline in Microsoft Fabric via REST API.

.PARAMETER WorkspaceId
    The GUID of your Fabric workspace.

.PARAMETER NotebookId
    The GUID of the imported Tenant_Settings_Change_Tracker notebook item.

.PARAMETER Email
    The recipient email address for change alert notifications.

.PARAMETER OutlookConnectionId
    (Optional) The GUID of the Outlook connection created in Fabric Settings -> Connections.
    If omitted, the pipeline is deployed without the Outlook activity wired up.

.PARAMETER PipelineItemId
    (Optional) The GUID of an existing pipeline item to update.
    If omitted, a new pipeline item is created.

.EXAMPLE
    .\deploy.ps1 `
        -WorkspaceId  "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" `
        -NotebookId   "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy" `
        -Email        "you@company.com" `
        -OutlookConnectionId "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"
#>

param(
    [Parameter(Mandatory)]
    [string] $WorkspaceId,

    [Parameter(Mandatory)]
    [string] $NotebookId,

    [Parameter(Mandatory)]
    [string] $Email,

    [string] $OutlookConnectionId = "<OUTLOOK_CONNECTION_ID>",

    [string] $PipelineItemId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# 1. Read and patch the pipeline JSON
# ---------------------------------------------------------------------------
$jsonPath = Join-Path $PSScriptRoot "pipeline-content.json"
$pipelineJson = Get-Content $jsonPath -Raw

$pipelineJson = $pipelineJson `
    -replace "<WORKSPACE_ID>",          $WorkspaceId `
    -replace "<NOTEBOOK_ID>",           $NotebookId `
    -replace "<YOUR_EMAIL>",            $Email `
    -replace "<OUTLOOK_CONNECTION_ID>", $OutlookConnectionId

# Validate it's still valid JSON
try {
    $null = $pipelineJson | ConvertFrom-Json
} catch {
    Write-Error "pipeline-content.json is not valid JSON after substitution: $_"
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Obtain an access token via Azure CLI
# ---------------------------------------------------------------------------
Write-Host "Acquiring Fabric access token via Azure CLI..." -ForegroundColor Cyan
$tokenJson = az account get-access-token --resource "https://api.fabric.microsoft.com" --query "{token:accessToken}" -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "az account get-access-token failed. Make sure you are logged in: az login"
    exit 1
}
$accessToken = ($tokenJson | ConvertFrom-Json).token

$headers = @{
    "Authorization" = "Bearer $accessToken"
    "Content-Type"  = "application/json"
}

# ---------------------------------------------------------------------------
# 3. Base64-encode the pipeline payload
# ---------------------------------------------------------------------------
$payloadBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pipelineJson))

$body = @{
    displayName = "Tenant_Settings_Alert_Pipeline"
    type        = "DataPipeline"
    definition  = @{
        parts = @(
            @{
                path        = "pipeline-content.json"
                payload     = $payloadBase64
                payloadType = "InlineBase64"
            }
        )
    }
} | ConvertTo-Json -Depth 10

# ---------------------------------------------------------------------------
# 4. Create or update the pipeline item
# ---------------------------------------------------------------------------
$baseUrl = "https://api.fabric.microsoft.com/v1/workspaces/$WorkspaceId/items"

if ($PipelineItemId -ne "") {
    # Update existing pipeline
    $url = "$baseUrl/$PipelineItemId/updateDefinition"
    Write-Host "Updating existing pipeline item $PipelineItemId ..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $body
    Write-Host "Pipeline updated successfully." -ForegroundColor Green
} else {
    # Create new pipeline
    Write-Host "Creating new pipeline in workspace $WorkspaceId ..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri $baseUrl -Method Post -Headers $headers -Body $body
    $newItemId = $response.id
    Write-Host "Pipeline created successfully." -ForegroundColor Green
    Write-Host "  Item ID : $newItemId" -ForegroundColor Yellow
    Write-Host "  Save this ID and pass it as -PipelineItemId on future updates." -ForegroundColor Yellow
}
