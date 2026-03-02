<#
  Usage:
    ./push_to_azure.ps1                 # auto timestamp tag
    ./push_to_azure.ps1 -Tag v1.2.3      # custom tag

  What it does:
    1) docker compose build (local)
    2) tags both images with $Tag and pushes to ACR
    3) emits a tiny compose file pointing at those tags
    4) az webapp config container set … → forces App Service to pull & restart
#>

param(
  [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"

# ─── CONFIG: adjust once ────────────────────────────────────────────
$RG  = "litsearch-rg"       # Azure resource‑group
$APP = "litsearch-app"      # Web App name (must already exist)
$ACR = "litsearchacr"       # ACR name (no loginServer)
# Ensure logged in (run 'az login' manually first, or 'az login --tenant YOUR_TENANT_ID')
az account show 2>$null | Out-Null; if (-not $?) { az login }

# ───────────────────────────────────────────────────────────────────

$ACR_LOGIN = (az acr show -n $ACR --query loginServer -o tsv)

Write-Host "[1/5] build images…" -f Cyan

docker compose build

Write-Host "[2/5] tag & push -> $Tag" -f Cyan

az acr login -n $ACR | Out-Null   # noop if already authed

docker tag litsearch-backend:latest  "$ACR_LOGIN/litsearch-backend:$Tag"
docker tag litsearch-frontend:latest "$ACR_LOGIN/litsearch-frontend:$Tag"

docker push "$ACR_LOGIN/litsearch-backend:$Tag"
docker push "$ACR_LOGIN/litsearch-frontend:$Tag"

Write-Host "[3/5] generate compose snippet" -f Cyan

$compose = @"
version: '3.9'
services:
  backend:
    image: $ACR_LOGIN/litsearch-backend:$Tag
    restart: always
    ports:
      - '8000:8000'
  frontend:
    image: $ACR_LOGIN/litsearch-frontend:$Tag
    restart: always
    ports:
      - '80:80'
    depends_on:
      - backend
"@

$tempFile = "docker-compose.azure.gen.yml"
$compose | Out-File -Encoding UTF8 $tempFile

Write-Host "[4/5] update Web App configuration" -f Cyan

az webapp config container set `
    --name $APP `
    --resource-group $RG `
    --multicontainer-config-type compose `
    --multicontainer-config-file $tempFile

Write-Host "[5/5] done!  Tail logs with:`n   az webapp log tail -n $APP -g $RG" -f Green