# PowerShell script for Azure resource setup

$ErrorActionPreference = "Stop"

Write-Host "=== Azure Multimodal RAG Pipeline - Resource Setup ===" -ForegroundColor Cyan

$RESOURCE_GROUP = if ($env:AZURE_RESOURCE_GROUP) { $env:AZURE_RESOURCE_GROUP } else { "multimodal-rag-rg" }
$LOCATION = if ($env:AZURE_LOCATION) { $env:AZURE_LOCATION } else { "eastus" }
$STORAGE_ACCOUNT = if ($env:AZURE_STORAGE_ACCOUNT_NAME) { $env:AZURE_STORAGE_ACCOUNT_NAME } else { "oemstorageacct" }
$FUNCTION_APP = if ($env:AZURE_FUNCTION_APP_NAME) { $env:AZURE_FUNCTION_APP_NAME } else { "oem-processor-func" }
$APP_INSIGHTS = if ($env:AZURE_APP_INSIGHTS_NAME) { $env:AZURE_APP_INSIGHTS_NAME } else { "oem-insights" }
$SEARCH_SERVICE = if ($env:AZURE_SEARCH_SERVICE_NAME) { $env:AZURE_SEARCH_SERVICE_NAME } else { "oem-search" }
$SQL_SERVER = if ($env:AZURE_SQL_SERVER_NAME) { $env:AZURE_SQL_SERVER_NAME } else { "oem-sql-server" }
$SQL_DATABASE = if ($env:AZURE_SQL_DATABASE) { $env:AZURE_SQL_DATABASE } else { "logging_db" }
$DOC_INTEL = if ($env:AZURE_DOC_INTEL_NAME) { $env:AZURE_DOC_INTEL_NAME } else { "oem-doc-intel" }
$OPENAI_SERVICE = if ($env:AZURE_OPENAI_NAME) { $env:AZURE_OPENAI_NAME } else { "oem-openai" }

Write-Host "Creating resource group: $RESOURCE_GROUP" -ForegroundColor Green
az group create --name $RESOURCE_GROUP --location $LOCATION

Write-Host "Creating storage account: $STORAGE_ACCOUNT" -ForegroundColor Green
az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku Standard_LRS `
  --kind StorageV2 `
  --allow-blob-public-access false

Write-Host "Creating blob containers..." -ForegroundColor Green
az storage container create `
  --name raw-documents `
  --account-name $STORAGE_ACCOUNT `
  --auth-mode login

az storage container create `
  --name processed-documents `
  --account-name $STORAGE_ACCOUNT `
  --auth-mode login

Write-Host "Creating Application Insights: $APP_INSIGHTS" -ForegroundColor Green
az monitor app-insights component create `
  --app $APP_INSIGHTS `
  --location $LOCATION `
  --resource-group $RESOURCE_GROUP `
  --application-type web

Write-Host "Creating Azure Cognitive Search: $SEARCH_SERVICE" -ForegroundColor Green
az search service create `
  --name $SEARCH_SERVICE `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku standard

Write-Host "Creating Azure SQL Server: $SQL_SERVER" -ForegroundColor Green
az sql server create `
  --name $SQL_SERVER `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --admin-user sqladmin `
  --enable-ad-only-auth

Write-Host "Creating SQL Database: $SQL_DATABASE" -ForegroundColor Green
az sql db create `
  --resource-group $RESOURCE_GROUP `
  --server $SQL_SERVER `
  --name $SQL_DATABASE `
  --service-objective S0 `
  --backup-storage-redundancy Local

Write-Host "Creating Document Intelligence: $DOC_INTEL" -ForegroundColor Green
az cognitiveservices account create `
  --name $DOC_INTEL `
  --resource-group $RESOURCE_GROUP `
  --kind FormRecognizer `
  --sku S0 `
  --location $LOCATION `
  --yes

Write-Host "Creating Azure OpenAI: $OPENAI_SERVICE" -ForegroundColor Green
az cognitiveservices account create `
  --name $OPENAI_SERVICE `
  --resource-group $RESOURCE_GROUP `
  --kind OpenAI `
  --sku S0 `
  --location $LOCATION `
  --yes

Write-Host "Creating Function App: $FUNCTION_APP" -ForegroundColor Green
az functionapp create `
  --name $FUNCTION_APP `
  --storage-account $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --consumption-plan-location $LOCATION `
  --runtime python `
  --runtime-version 3.11 `
  --functions-version 4 `
  --os-type Linux

Write-Host "Enabling managed identity..." -ForegroundColor Green
az functionapp identity assign `
  --name $FUNCTION_APP `
  --resource-group $RESOURCE_GROUP

$FUNCTION_IDENTITY = az functionapp identity show `
  --name $FUNCTION_APP `
  --resource-group $RESOURCE_GROUP `
  --query principalId -o tsv

Write-Host "Assigning RBAC roles..." -ForegroundColor Green

$subscriptionId = az account show --query id -o tsv

az role assignment create `
  --assignee $FUNCTION_IDENTITY `
  --role "Storage Blob Data Contributor" `
  --scope "/subscriptions/$subscriptionId/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

Write-Host ""
Write-Host "=== Resource Setup Complete ===" -ForegroundColor Cyan
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Yellow
Write-Host "Storage Account: $STORAGE_ACCOUNT" -ForegroundColor Yellow
Write-Host "Function App: $FUNCTION_APP" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Run database migrations: alembic upgrade head"
Write-Host "2. Deploy function app: func azure functionapp publish $FUNCTION_APP"
Write-Host "3. Create search index via API endpoint"
