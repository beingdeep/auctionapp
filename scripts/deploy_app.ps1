param(
    [Parameter(Mandatory = $true)]
    [string]$EnvFile
)

$ErrorActionPreference = "Stop"

# Build/push the current app image and update existing Container App.
# Usage:
# .\scripts\deploy_app.ps1 -EnvFile .azure/auctionapp-dev.env

if (-not (Test-Path -Path $EnvFile -PathType Leaf)) {
    throw "Env file not found: $EnvFile"
}

function Import-ShellEnvFile {
    param([string]$Path)

    $vars = @{}
    foreach ($line in Get-Content -Path $Path) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.TrimStart().StartsWith("#")) { continue }

        if ($line -match '^(?<key>[A-Za-z_][A-Za-z0-9_]*)=(?<value>.*)$') {
            $key = $Matches['key']
            $value = $Matches['value'].Trim()

            if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            $vars[$key] = $value
        }
    }

    return $vars
}

$envVars = Import-ShellEnvFile -Path $EnvFile

$required = @(
    'SUBSCRIPTION',
    'RESOURCE_GROUP',
    'ACR_LOGIN_SERVER',
    'CONTAINER_APP_NAME',
    'PROJECT',
    'ENVIRONMENT'
)

foreach ($name in $required) {
    if (-not $envVars.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($envVars[$name])) {
        throw "$name missing in env file"
    }
}

$Subscription = $envVars['SUBSCRIPTION']
$ResourceGroup = $envVars['RESOURCE_GROUP']
$AcrLoginServer = $envVars['ACR_LOGIN_SERVER']
$ContainerAppName = $envVars['CONTAINER_APP_NAME']
$Project = $envVars['PROJECT']
$Environment = $envVars['ENVIRONMENT']

az account set --subscription $Subscription | Out-Null

$GitSha = git rev-parse --short HEAD
$ImageTag = "$AcrLoginServer/$Project:$Environment-$GitSha"
$AcrName = $AcrLoginServer.Split('.')[0]

az acr build --registry $AcrName --image $ImageTag .

az containerapp update `
  --name $ContainerAppName `
  --resource-group $ResourceGroup `
  --image $ImageTag | Out-Null

$AppFqdn = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv

Write-Host "Application deployment complete"
Write-Host "Live URL: https://$AppFqdn"
