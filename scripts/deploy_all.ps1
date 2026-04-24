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

# Deploy infrastructure then deploy the app image.
# Usage:
# .\scripts\deploy_all.ps1 `
#   -Subscription "<subscription-id-or-name>" `
#   -ResourceGroup "rg-auction-dev" `
#   -Location "eastus" `
#   -Project "auctionapp" `
#   -Env "dev" `
#   -PostgresPassword "<strong-password>" `
#   -DjangoSecret "<django-secret-key>"

& "$PSScriptRoot/deploy_infra.ps1" `
    -Subscription $Subscription `
    -ResourceGroup $ResourceGroup `
    -Location $Location `
    -Project $Project `
    -Env $Env `
    -PostgresPassword $PostgresPassword `
    -DjangoSecret $DjangoSecret

& "$PSScriptRoot/deploy_app.ps1" -EnvFile ".azure/$Project-$Env.env"
