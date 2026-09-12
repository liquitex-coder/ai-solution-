# WordPress auto-initialization (PowerShell port of wp-init.sh, requirements §24).
# For Windows environments without a working WSL bash.
#
# Usage:
#   $env:WP_BEARER_TOKEN = $token
#   $env:WP_SITE = "liquitex929aa21393-eyqci.wordpress.com"
#   powershell -ExecutionPolicy Bypass -File scripts/wp-init.ps1
#
# Auth: WP_BEARER_TOKEN + WP_SITE (WordPress.com production) takes precedence
# over WP_USERNAME + WP_APP_PASSWORD (self-hosted sandbox), mirroring
# scripts/wp-init.sh.

$ErrorActionPreference = "Stop"

$WpUrl = if ($env:WP_URL) { $env:WP_URL } else { "http://localhost:8080" }
$WpSite = $env:WP_SITE
$WpUsername = if ($env:WP_USERNAME) { $env:WP_USERNAME } else { "admin" }
$WpAppPassword = $env:WP_APP_PASSWORD
$WpBearerToken = $env:WP_BEARER_TOKEN

if ($WpBearerToken) {
    if (-not $WpSite) {
        Write-Error "WP_BEARER_TOKEN is set but WP_SITE is not. WP_SITE must be the site's unmapped wordpress.com domain (e.g. liquitex929aa21393-eyqci.wordpress.com)."
        exit 1
    }
    $Headers = @{ Authorization = "Bearer $WpBearerToken" }
    $AuthDesc = "Bearer (WP_BEARER_TOKEN) - WordPress.com production"
    $ApiBase = "https://public-api.wordpress.com/wp/v2/sites/$WpSite"
}
elseif ($WpAppPassword) {
    $Pair = "$($WpUsername):$($WpAppPassword)"
    $Encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Pair))
    $Headers = @{ Authorization = "Basic $Encoded" }
    $AuthDesc = "Basic ($WpUsername) - self-hosted sandbox"
    $ApiBase = "$($WpUrl.TrimEnd('/'))/wp-json/wp/v2"
}
else {
    Write-Error "No credentials set. Set WP_BEARER_TOKEN + WP_SITE (WordPress.com production) or WP_USERNAME + WP_APP_PASSWORD (self-hosted sandbox)."
    exit 1
}

$TaxonomyFile = Join-Path $PSScriptRoot "..\data\wp-taxonomy.json"

function Test-Auth {
    try {
        $resp = Invoke-RestMethod -Uri "$ApiBase/users/me" -Headers $Headers -Method Get
        Write-Host "[OK] Authentication verified. ($($resp.name))"
    }
    catch {
        $status = $_.Exception.Response.StatusCode.value__
        Write-Error "Authentication failed (HTTP $status) using $AuthDesc."
        if ($WpBearerToken) {
            Write-Error "Check that the access_token is still valid (requirements section 24)."
        }
        else {
            Write-Error "Basic auth on WordPress.com with two-step auth active returns 401 (invalid_token) - use WP_BEARER_TOKEN instead (requirements section 24)."
        }
        exit 1
    }
}

function New-WpCategory {
    param([string]$Name, [string]$Slug, [string]$Description)
    $existing = Invoke-RestMethod -Uri "$ApiBase/categories?slug=$Slug" -Headers $Headers -Method Get
    if ($existing.Count -gt 0) {
        Write-Host "[SKIP] Category already exists: $Name ($Slug)"
        return
    }
    $body = @{ name = $Name; slug = $Slug; description = $Description } | ConvertTo-Json -Compress
    try {
        $result = Invoke-RestMethod -Uri "$ApiBase/categories" -Headers $Headers -Method Post -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "[CREATED] Category: $Name (id=$($result.id))"
    }
    catch {
        Write-Warning "Failed to create category: $Name - $($_.Exception.Message)"
    }
}

function New-WpTag {
    param([string]$Name, [string]$Slug)
    $existing = Invoke-RestMethod -Uri "$ApiBase/tags?slug=$Slug" -Headers $Headers -Method Get
    if ($existing.Count -gt 0) {
        Write-Host "[SKIP] Tag already exists: $Name ($Slug)"
        return
    }
    $body = @{ name = $Name; slug = $Slug } | ConvertTo-Json -Compress
    try {
        $result = Invoke-RestMethod -Uri "$ApiBase/tags" -Headers $Headers -Method Post -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "[CREATED] Tag: $Name (id=$($result.id))"
    }
    catch {
        Write-Warning "Failed to create tag: $Name - $($_.Exception.Message)"
    }
}

Write-Host "=== WordPress Initialization ==="
Write-Host "Target: $ApiBase"
Write-Host "Auth:   $AuthDesc"
Write-Host ""

Test-Auth
Write-Host ""

$Taxonomy = Get-Content -Raw -Path $TaxonomyFile -Encoding UTF8 | ConvertFrom-Json

Write-Host "--- Creating categories ---"
foreach ($cat in $Taxonomy.categories) {
    New-WpCategory -Name $cat.name -Slug $cat.slug -Description $cat.description
}

Write-Host ""
Write-Host "--- Creating tags ---"
foreach ($tag in $Taxonomy.tags) {
    New-WpTag -Name $tag.name -Slug $tag.slug
}

Write-Host ""
Write-Host "=== Initialization complete ==="
