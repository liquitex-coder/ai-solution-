# n8n cloud API deployment automation (requirements §25).
# Creates credentials (from whichever env vars are set) and imports the 9
# workflow JSONs, wiring each node's credential placeholder to the real
# created credential id. Idempotent: skips credentials/workflows that
# already exist by name. Does NOT activate workflows — activation stays a
# manual, human-verified step (staged rollout, see SETUP_GUIDE.md Step 5).
#
# Usage:
#   $env:N8N_API_KEY = "..."
#   $env:N8N_BASE_URL = "https://liquitex-coder.app.n8n.cloud/api/v1"  # optional, this is the default
#   $env:ANTHROPIC_API_KEY = "..."
#   $env:WP_BEARER_TOKEN = "..."
#   # optional: GITHUB_TOKEN, PERPLEXITY_API_KEY, KIMI_API_KEY, THREADS_ACCESS_TOKEN, YOUTUBE_API_KEY
#   powershell -ExecutionPolicy Bypass -File scripts/n8n_deploy.ps1

$ErrorActionPreference = "Stop"

if (-not $env:N8N_API_KEY) {
    Write-Error "N8N_API_KEY is not set. Create one at Settings > n8n API in the n8n UI."
    exit 1
}
$BaseUrl = if ($env:N8N_BASE_URL) { $env:N8N_BASE_URL } else { "https://liquitex-coder.app.n8n.cloud/api/v1" }
$Headers = @{
    "X-N8N-API-KEY" = $env:N8N_API_KEY
    "Content-Type"  = "application/json"
}

# name -> (credential type, header/query param name, env var, value prefix, required)
$CredentialDefs = [ordered]@{
    "Claude API Key"           = @{ Type = "httpHeaderAuth"; Header = "x-api-key";     EnvVar = "ANTHROPIC_API_KEY";     Prefix = "";       Required = $true  }
    "WordPress App Password"   = @{ Type = "httpHeaderAuth"; Header = "Authorization"; EnvVar = "WP_BEARER_TOKEN";        Prefix = "Bearer "; Required = $true  }
    "GitHub API Token"         = @{ Type = "httpHeaderAuth"; Header = "Authorization"; EnvVar = "GITHUB_TOKEN";           Prefix = "token ";  Required = $false }
    "Perplexity API Key"       = @{ Type = "httpHeaderAuth"; Header = "Authorization"; EnvVar = "PERPLEXITY_API_KEY";     Prefix = "Bearer "; Required = $false }
    "Kimi API Key"             = @{ Type = "httpHeaderAuth"; Header = "Authorization"; EnvVar = "KIMI_API_KEY";           Prefix = "Bearer "; Required = $false }
    "Threads API Token"        = @{ Type = "httpHeaderAuth"; Header = "Authorization"; EnvVar = "THREADS_ACCESS_TOKEN";   Prefix = "Bearer "; Required = $false }
    # requirements §25-4 resolved: the node now uses httpQueryAuth, matching
    # how Google's YouTube Data API actually expects the key (query param).
    "YouTube Data API Key"     = @{ Type = "httpQueryAuth";  Header = "key";           EnvVar = "YOUTUBE_API_KEY";        Prefix = "";       Required = $false }
}

Write-Host "=== n8n Deployment (requirements section 25) ==="
Write-Host "Target: $BaseUrl"
Write-Host ""

# ---- fetch existing credentials/workflows for idempotency ----
$existingCreds = (Invoke-RestMethod -Uri "$BaseUrl/credentials" -Headers $Headers -Method Get).data
$existingWorkflows = (Invoke-RestMethod -Uri "$BaseUrl/workflows" -Headers $Headers -Method Get).data

$credentialIds = @{}
foreach ($existing in $existingCreds) {
    $credentialIds[$existing.name] = $existing.id
}

Write-Host "--- Creating credentials ---"
foreach ($name in $CredentialDefs.Keys) {
    $def = $CredentialDefs[$name]
    $value = [Environment]::GetEnvironmentVariable($def.EnvVar)

    if ($credentialIds.ContainsKey($name)) {
        Write-Host "[SKIP] Credential already exists: $name"
        continue
    }
    if (-not $value) {
        if ($def.Required) {
            Write-Error "Required env var $($def.EnvVar) is not set (needed for credential '$name')."
            exit 1
        }
        Write-Host "[SKIP] $($def.EnvVar) not set - skipping optional credential: $name"
        continue
    }

    $body = @{
        name = $name
        type = $def.Type
        data = @{
            name  = $def.Header
            value = "$($def.Prefix)$value"
        }
    } | ConvertTo-Json -Compress

    try {
        $result = Invoke-RestMethod -Uri "$BaseUrl/credentials" -Headers $Headers -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($body))
        $credentialIds[$name] = $result.id
        Write-Host "[CREATED] Credential: $name (id=$($result.id))"
    }
    catch {
        Write-Warning "Failed to create credential '$name': $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "--- Importing workflows ---"

$workflowDir = Join-Path $PSScriptRoot "..\n8n\workflows"
$workflowFiles = Get-ChildItem -Path $workflowDir -Filter "*.json" | Sort-Object Name

foreach ($file in $workflowFiles) {
    $wf = Get-Content -Raw -Path $file.FullName -Encoding UTF8 | ConvertFrom-Json

    $already = $existingWorkflows | Where-Object { $_.name -eq $wf.name }
    if ($already) {
        Write-Host "[SKIP] Workflow already exists: $($wf.name)"
        continue
    }

    $missingCreds = @()
    foreach ($node in $wf.nodes) {
        if ($node.credentials) {
            foreach ($credType in $node.credentials.PSObject.Properties.Name) {
                $credRef = $node.credentials.$credType
                if ($credentialIds.ContainsKey($credRef.name)) {
                    $credRef.id = $credentialIds[$credRef.name]
                }
                else {
                    $missingCreds += $credRef.name
                }
            }
        }
    }

    # n8n's create-workflow API accepts only this subset; strip everything else
    # (active/tags/notes are not part of the accepted schema).
    $payload = @{
        name        = $wf.name
        nodes       = $wf.nodes
        connections = $wf.connections
        settings    = if ($wf.settings) { $wf.settings } else { @{} }
    } | ConvertTo-Json -Depth 50 -Compress

    try {
        $result = Invoke-RestMethod -Uri "$BaseUrl/workflows" -Headers $Headers -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($payload))
        $note = if ($missingCreds.Count -gt 0) { " (missing creds, fix manually: $($missingCreds -join ', '))" } else { "" }
        Write-Host "[CREATED] Workflow: $($wf.name) (id=$($result.id))$note"
    }
    catch {
        Write-Warning "Failed to import workflow '$($file.Name)': $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "=== Deployment complete ==="
Write-Host ""
Write-Host "Reminders (not automated by this script):"
Write-Host "  - GITHUB_TOKEN must be set as an n8n Environment variable (Settings > Environments)"
Write-Host "    for the prompt-loading Code nodes to fetch from GitHub - this is separate from credentials."
Write-Host "  - No workflow was activated. Manually execute each once, confirm a WordPress draft is"
Write-Host "    created, then toggle Active (SETUP_GUIDE.md Step 5)."
Write-Host "  - Set CLAIM_AUDITOR_URL and CLAIM_AUDITOR_MODE as n8n Environment/Variables for"
Write-Host "    production (n8n.cloud) use (SETUP_GUIDE.md Step 4b). The local docker-compose"
Write-Host "    sandbox already sets both automatically; this manual step is cloud-only."
