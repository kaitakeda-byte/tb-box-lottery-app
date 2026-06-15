# box-lottery-app Cloud Run deploy
# IMPORTANT: No Japanese chars (PS5.1 reads .ps1 as CP932)
$ErrorActionPreference = "Continue"

$PROJECT_ID = "torecabank-egosearch"
$REGION = "asia-northeast1"
$SERVICE_NAME = "box-lottery-app"

$myDir = $PSScriptRoot
if ([string]::IsNullOrEmpty($myDir)) { $myDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrEmpty($myDir)) { $myDir = (Get-Location).Path }
Set-Location $myDir

# Copy oauth_client.json from X-egosearch
$parentDir = Split-Path -Parent $myDir
$xegoDir = Join-Path $parentDir "X-egosearch"

Write-Host "==> Copying source files..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $xegoDir "oauth_client.json"))) {
    Write-Host "ERROR: oauth_client.json not found at $xegoDir" -ForegroundColor Red
    exit 1
}
Copy-Item -Force (Join-Path $xegoDir "oauth_client.json") .

# Load env from X-egosearch/.env
$envFile = Join-Path $xegoDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env not found at $envFile" -ForegroundColor Red
    exit 1
}
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.*)$') {
        $envVars[$Matches[1]] = $Matches[2].Trim('"').Trim("'")
    }
}

$required = @('SHEETS_OAUTH_REFRESH_TOKEN', 'SOCIALDATA_API_KEY')
foreach ($k in $required) {
    if (-not $envVars[$k]) {
        Write-Host "ERROR: $k missing in .env" -ForegroundColor Red
        exit 1
    }
}

# Generate or load APP_PASSWORD from local .env
$localEnvFile = Join-Path $myDir ".env"
$appPassword = $null
if (Test-Path $localEnvFile) {
    Get-Content $localEnvFile | ForEach-Object {
        if ($_ -match '^APP_PASSWORD=(.*)$') {
            $appPassword = $Matches[1].Trim('"').Trim("'")
        }
    }
}
if (-not $appPassword) {
    Add-Type -AssemblyName System.Web
    $appPassword = [System.Web.Security.Membership]::GeneratePassword(16, 0) -replace '[^a-zA-Z0-9]', 'x'
    "APP_PASSWORD=$appPassword" | Out-File -FilePath $localEnvFile -Encoding utf8
    Write-Host "==> New APP_PASSWORD generated and saved to box_lottery_app/.env" -ForegroundColor Yellow
}

Write-Host "==> Setting project: $PROJECT_ID" -ForegroundColor Cyan
gcloud config set project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "==> Enabling APIs" -ForegroundColor Cyan
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

Write-Host "==> Deploying to Cloud Run" -ForegroundColor Cyan
$envVarsArg = "SHEETS_OAUTH_REFRESH_TOKEN=$($envVars['SHEETS_OAUTH_REFRESH_TOKEN']),SOCIALDATA_API_KEY=$($envVars['SOCIALDATA_API_KEY']),APP_PASSWORD=$appPassword"

gcloud run deploy $SERVICE_NAME `
    --region $REGION `
    --source . `
    --memory 1Gi `
    --cpu 1 `
    --timeout 600 `
    --max-instances 1 `
    --allow-unauthenticated `
    --set-env-vars="$envVarsArg"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: deploy failed" -ForegroundColor Red
    exit 1
}

Write-Host "==> Deploy complete" -ForegroundColor Green
$serviceUrl = gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'
Write-Host "Service URL: $serviceUrl" -ForegroundColor Yellow

Write-Host ""
Write-Host "===== NEXT STEPS =====" -ForegroundColor Cyan
Write-Host "1. Service URL  : $serviceUrl"
Write-Host "2. APP_PASSWORD : $appPassword"
Write-Host "3. Share these with team members who need access"
