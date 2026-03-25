#!/bin/bash

set -e

echo "=== Azure Multimodal RAG Pipeline - Resource Setup ==="

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-multimodal-rag-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT_NAME:-oemstorageacct}"
FUNCTION_APP="${AZURE_FUNCTION_APP_NAME:-oem-processor-func}"
APP_INSIGHTS="${AZURE_APP_INSIGHTS_NAME:-oem-insights}"
SEARCH_SERVICE="${AZURE_SEARCH_SERVICE_NAME:-oem-search}"
SQL_SERVER="${AZURE_SQL_SERVER_NAME:-oem-sql-server}"
SQL_DATABASE="${AZURE_SQL_DATABASE:-logging_db}"
DOC_INTEL="${AZURE_DOC_INTEL_NAME:-oem-doc-intel}"
OPENAI_SERVICE="${AZURE_OPENAI_NAME:-oem-openai}"

echo "Creating resource group: $RESOURCE_GROUP"
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

echo "Creating storage account: $STORAGE_ACCOUNT"
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false

echo "Creating blob containers..."
az storage container create \
  --name raw-documents \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login

az storage container create \
  --name processed-documents \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login

echo "Creating Application Insights: $APP_INSIGHTS"
az monitor app-insights component create \
  --app $APP_INSIGHTS \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

echo "Creating Azure Cognitive Search: $SEARCH_SERVICE"
az search service create \
  --name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku standard

echo "Creating Azure SQL Server: $SQL_SERVER"
az sql server create \
  --name $SQL_SERVER \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --admin-user sqladmin \
  --enable-ad-only-auth

echo "Creating SQL Database: $SQL_DATABASE"
az sql db create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name $SQL_DATABASE \
  --service-objective S0 \
  --backup-storage-redundancy Local

echo "Creating Document Intelligence: $DOC_INTEL"
az cognitiveservices account create \
  --name $DOC_INTEL \
  --resource-group $RESOURCE_GROUP \
  --kind FormRecognizer \
  --sku S0 \
  --location $LOCATION \
  --yes

echo "Creating Azure OpenAI: $OPENAI_SERVICE"
az cognitiveservices account create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --kind OpenAI \
  --sku S0 \
  --location $LOCATION \
  --yes

echo "Deploying GPT-4 Vision model..."
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4-vision-preview \
  --model-name gpt-4 \
  --model-version vision-preview \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

echo "Deploying text-embedding-3-large model..."
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large \
  --model-version 1 \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

echo "Creating Function App: $FUNCTION_APP"
az functionapp create \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux

echo "Enabling managed identity for Function App..."
az functionapp identity assign \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

FUNCTION_IDENTITY=$(az functionapp identity show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query principalId -o tsv)

echo "Assigning RBAC roles..."

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Cognitive Services User" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$DOC_INTEL"

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Cognitive Services User" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE"

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Search Index Data Contributor" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$SEARCH_SERVICE"

echo "Configuring Function App settings..."
APP_INSIGHTS_KEY=$(az monitor app-insights component show \
  --app $APP_INSIGHTS \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    "APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_KEY" \
    "USE_MANAGED_IDENTITY=true" \
    "AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT" \
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://$DOC_INTEL.cognitiveservices.azure.com/" \
    "AZURE_OPENAI_ENDPOINT=https://$OPENAI_SERVICE.openai.azure.com/" \
    "AZURE_SEARCH_ENDPOINT=https://$SEARCH_SERVICE.search.windows.net" \
    "AZURE_SQL_SERVER=$SQL_SERVER.database.windows.net" \
    "AZURE_SQL_DATABASE=$SQL_DATABASE"

echo ""
echo "=== Resource Setup Complete ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Function App: $FUNCTION_APP"
echo "Search Service: $SEARCH_SERVICE"
echo "SQL Server: $SQL_SERVER"
echo ""
echo "Next steps:"
echo "1. Run database migrations: alembic upgrade head"
echo "2. Deploy function app: func azure functionapp publish $FUNCTION_APP"
echo "3. Create search index: curl -X POST https://$FUNCTION_APP.azurewebsites.net/api/create-index"
