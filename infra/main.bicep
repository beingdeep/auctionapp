@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Project/application prefix used to name resources.')
param projectName string = 'auctionapp'

@description('Container image including tag (example: myacr.azurecr.io/auctionapp:latest).')
param containerImage string

@description('Environment name (dev/test/prod).')
param environment string = 'dev'

@description('Container CPU cores.')
param containerCpu string = '0.5'

@description('Container memory allocation.')
param containerMemory string = '1.0Gi'

@secure()
@description('Django secret key used by the container app.')
param djangoSecretKey string

@secure()
@description('PostgreSQL admin password.')
param postgresAdminPassword string

@description('PostgreSQL admin username.')
param postgresAdminUser string = 'auctionadmin'

@description('PostgreSQL database name.')
param postgresDbName string = 'auctiondb'

var suffix = uniqueString(subscription().id, resourceGroup().id, projectName, environment)
var acrName = toLower(replace('${projectName}${environment}${suffix}', '-', ''))
var logAnalyticsName = '${projectName}-${environment}-law'
var managedEnvName = '${projectName}-${environment}-cae'
var containerAppName = '${projectName}-${environment}-app'
var postgresServerName = toLower('${projectName}-${environment}-${take(suffix, 6)}-pg')
var redisName = toLower('${projectName}-${environment}-${take(suffix, 6)}-redis')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource managedEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: managedEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: listKeys(logAnalytics.id, logAnalytics.apiVersion).primarySharedKey
      }
    }
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource redis 'Microsoft.Cache/Redis@2024-03-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: postgresDbName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acr.properties.loginServer
          identity: 'system'
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: [
        {
          name: 'db-password'
          value: postgresAdminPassword
        }
        {
          name: 'django-secret-key'
          value: djangoSecretKey
        }
        {
          name: 'redis-connection-string'
          value: '${redis.properties.hostName}:6380,password=${listKeys(redis.id, redis.apiVersion).primaryKey},ssl=True,abortConnect=False'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: containerImage
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: [
            {
              name: 'DJANGO_SECRET_KEY'
              secretRef: 'django-secret-key'
            }
            {
              name: 'DJANGO_ALLOWED_HOSTS'
              value: '*'
            }
            {
              name: 'DJANGO_DEBUG'
              value: 'False'
            }
            {
              name: 'DATABASE_NAME'
              value: postgresDbName
            }
            {
              name: 'DATABASE_USER'
              value: postgresAdminUser
            }
            {
              name: 'DATABASE_PASSWORD'
              secretRef: 'db-password'
            }
            {
              name: 'DATABASE_HOST'
              value: '${postgres.name}.postgres.database.azure.com'
            }
            {
              name: 'DATABASE_PORT'
              value: '5432'
            }
            {
              name: 'REDIS_CONNECTION_STRING'
              secretRef: 'redis-connection-string'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
  dependsOn: [
    postgresDb
    allowAzureServices
    redis
  ]
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(app.id, acr.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: app.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}

output containerAppUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
output containerAppName string = app.name
output acrLoginServer string = acr.properties.loginServer
output redisHost string = redis.properties.hostName
output postgresFqdn string = '${postgres.name}.postgres.database.azure.com'
output postgresDatabase string = postgresDbName
output postgresUser string = '${postgresAdminUser}'
