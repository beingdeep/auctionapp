param(
    [Parameter(Mandatory = $true)]
    [string]$Subscription,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$Location,

    [Parameter(Mandatory = $true)]
    [string]$Project,

    [Parameter(Mandatory = $true)]
    [string]$Env,

    [Parameter(Mandatory = $true)]
    [string]$PostgresPassword,

    [Parameter(Mandatory = $true)]
    [string]$DjangoSecret
)

$ErrorActionPreference = "Stop"

# Deploy foundational Azure resources (ACR, ACA env/app, PostgreSQL, Redis).
# Usage:
# .\scripts\deploy_infra.ps1 `
#   -Subscription "<subscription-id-or-name>" `
#   -ResourceGroup "rg-auction-dev" `
#   -Location "eastus" `
#   -Project "auctionapp" `
#   -Env "dev" `
#   -PostgresPassword "<strong-password>" `
#   -DjangoSecret "<django-secret-key>"

az account set --subscription $Subscription | Out-Null
az group create --name $ResourceGroup --location $Location | Out-Null

$DeploymentName = "$Project-$Env-infra-$(Get-Date -Format 'yyyyMMddHHmmss')"
$PlaceholderImage = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"

az deployment group create `
  --name $DeploymentName `
  --resource-group $ResourceGroup `
  --template-file infra/main.bicep `
  --parameters `
    projectName=$Project `
    environment=$Env `
    containerImage=$PlaceholderImage `
    postgresAdminPassword=$PostgresPassword `
    djangoSecretKey=$DjangoSecret | Out-Null

New-Item -ItemType Directory -Path ".azure" -Force | Out-Null
$OutputFile = ".azure/$Project-$Env.env"

$AcrLoginServer = az deployment group show --name $DeploymentName --resource-group $ResourceGroup --query properties.outputs.acrLoginServer.value -o tsv
$ContainerAppName = az deployment group show --name $DeploymentName --resource-group $ResourceGroup --query properties.outputs.containerAppName.value -o tsv
$ContainerAppUrl = az deployment group show --name $DeploymentName --resource-group $ResourceGroup --query properties.outputs.containerAppUrl.value -o tsv

@"
SUBSCRIPTION="$Subscription"
RESOURCE_GROUP="$ResourceGroup"
PROJECT="$Project"
ENVIRONMENT="$Env"
ACR_LOGIN_SERVER="$AcrLoginServer"
CONTAINER_APP_NAME="$ContainerAppName"
CONTAINER_APP_URL="$ContainerAppUrl"
"@ | Set-Content -Path $OutputFile

Write-Host "Infrastructure deployment complete"
Write-Host "Saved deployment outputs to: $OutputFile"
Write-Host "Container App URL (placeholder image): $ContainerAppUrl"
