# 🚀 Deployment Guide

Complete step-by-step guide for deploying the enterprise multimodal RAG pipeline to Azure.

---

## Prerequisites Checklist

- [ ] Azure Subscription with Owner/Contributor access
- [ ] Azure CLI installed (`az --version`)
- [ ] Python 3.11+ installed
- [ ] Azure Functions Core Tools v4 (`func --version`)
- [ ] Git installed
- [ ] Visual Studio Code (recommended)

---

## Step 1: Initial Setup

### 1.1 Clone Repository

```bash
git clone <repository-url>
cd Azure_Information_Extraction
```

### 1.2 Create Virtual Environment

**Linux/Mac:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 1.3 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 2: Azure Authentication

### 2.1 Login to Azure

```bash
az login
```

### 2.2 Set Default Subscription

```bash
az account list --output table
az account set --subscription "<subscription-id>"
```

### 2.3 Verify Authentication

```bash
az account show
```

---

## Step 3: Configure Environment

### 3.1 Copy Environment Template

```bash
cp .env.example .env
```

### 3.2 Set Resource Names

Edit `.env` and set unique names:

```bash
# Example values - MUST be globally unique
AZURE_STORAGE_ACCOUNT_NAME=oemstorageacct12345
AZURE_FUNCTION_APP_NAME=oem-processor-func-12345
AZURE_SEARCH_SERVICE_NAME=oem-search-12345
AZURE_SQL_SERVER_NAME=oem-sql-server-12345
AZURE_DOC_INTEL_NAME=oem-doc-intel-12345
AZURE_OPENAI_NAME=oem-openai-12345
```

---

## Step 4: Deploy Azure Resources

### 4.1 Set Environment Variables

**Linux/Mac:**
```bash
export AZURE_RESOURCE_GROUP="multimodal-rag-rg"
export AZURE_LOCATION="eastus"
export AZURE_STORAGE_ACCOUNT_NAME="oemstorageacct12345"
export AZURE_FUNCTION_APP_NAME="oem-processor-func-12345"
export AZURE_SEARCH_SERVICE_NAME="oem-search-12345"
export AZURE_SQL_SERVER_NAME="oem-sql-server-12345"
export AZURE_DOC_INTEL_NAME="oem-doc-intel-12345"
export AZURE_OPENAI_NAME="oem-openai-12345"
export AZURE_APP_INSIGHTS_NAME="oem-insights-12345"
```

**Windows PowerShell:**
```powershell
$env:AZURE_RESOURCE_GROUP="multimodal-rag-rg"
$env:AZURE_LOCATION="eastus"
$env:AZURE_STORAGE_ACCOUNT_NAME="oemstorageacct12345"
# ... (set all variables)
```

### 4.2 Run Deployment Script

**Linux/Mac:**
```bash
chmod +x deployment/setup_azure_resources.sh
./deployment/setup_azure_resources.sh
```

**Windows:**
```powershell
.\deployment\setup_azure_resources.ps1
```

**Expected Duration**: 10-15 minutes

### 4.3 Verify Resource Creation

```bash
az resource list --resource-group $AZURE_RESOURCE_GROUP --output table
```

---

## Step 5: Configure Database

### 5.1 Update Connection String

Get SQL connection details:

```bash
az sql server show --name $AZURE_SQL_SERVER_NAME --resource-group $AZURE_RESOURCE_GROUP
```

Update `.env` with SQL server details.

### 5.2 Configure Firewall

Allow your IP for migration:

```bash
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create \
  --resource-group $AZURE_RESOURCE_GROUP \
  --server $AZURE_SQL_SERVER_NAME \
  --name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

### 5.3 Run Database Migrations

```bash
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

### 5.4 Verify Tables

```bash
az sql db show-connection-string \
  --client sqlcmd \
  --name $AZURE_SQL_DATABASE \
  --server $AZURE_SQL_SERVER_NAME
```

---

## Step 6: Configure Azure OpenAI

### 6.1 Deploy GPT-4 Vision Model

```bash
az cognitiveservices account deployment create \
  --name $AZURE_OPENAI_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --deployment-name gpt-4-vision-preview \
  --model-name gpt-4 \
  --model-version vision-preview \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

### 6.2 Deploy Embedding Model

```bash
az cognitiveservices account deployment create \
  --name $AZURE_OPENAI_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large \
  --model-version 1 \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

### 6.3 Verify Deployments

```bash
az cognitiveservices account deployment list \
  --name $AZURE_OPENAI_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --output table
```

---

## Step 7: Deploy Function App

### 7.1 Build Function Package

```bash
# Ensure you're in the project root
func extensions install
```

### 7.2 Deploy to Azure

```bash
func azure functionapp publish $AZURE_FUNCTION_APP_NAME --python
```

**Expected Duration**: 3-5 minutes

### 7.3 Configure Application Settings

```bash
# Get Application Insights connection string
APP_INSIGHTS_KEY=$(az monitor app-insights component show \
  --app $AZURE_APP_INSIGHTS_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --query connectionString -o tsv)

# Configure function app
az functionapp config appsettings set \
  --name $AZURE_FUNCTION_APP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --settings \
    "APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_KEY" \
    "USE_MANAGED_IDENTITY=true" \
    "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)" \
    "AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)" \
    "AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP" \
    "AZURE_STORAGE_ACCOUNT_NAME=$AZURE_STORAGE_ACCOUNT_NAME" \
    "AZURE_STORAGE_CONTAINER_RAW=raw-documents" \
    "AZURE_STORAGE_CONTAINER_PROCESSED=processed-documents" \
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://$AZURE_DOC_INTEL_NAME.cognitiveservices.azure.com/" \
    "AZURE_OPENAI_ENDPOINT=https://$AZURE_OPENAI_NAME.openai.azure.com/" \
    "AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4-vision-preview" \
    "AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding-3-large" \
    "AZURE_OPENAI_API_VERSION=2024-02-15-preview" \
    "AZURE_SEARCH_ENDPOINT=https://$AZURE_SEARCH_SERVICE_NAME.search.windows.net" \
    "AZURE_SEARCH_INDEX_NAME=oem-documents" \
    "AZURE_SQL_SERVER=$AZURE_SQL_SERVER_NAME.database.windows.net" \
    "AZURE_SQL_DATABASE=logging_db" \
    "CONFIDENCE_THRESHOLD=0.85" \
    "ENABLE_EVALUATION=true"
```

---

## Step 8: Configure RBAC Permissions

### 8.1 Get Function App Identity

```bash
FUNCTION_IDENTITY=$(az functionapp identity show \
  --name $AZURE_FUNCTION_APP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --query principalId -o tsv)

echo "Function Identity: $FUNCTION_IDENTITY"
```

### 8.2 Assign Storage Permissions

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT_NAME"
```

### 8.3 Assign Cognitive Services Permissions

```bash
az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Cognitive Services User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$AZURE_DOC_INTEL_NAME"

az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Cognitive Services User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$AZURE_OPENAI_NAME"
```

### 8.4 Assign Search Permissions

```bash
az role assignment create \
  --assignee $FUNCTION_IDENTITY \
  --role "Search Index Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AZURE_SEARCH_SERVICE_NAME"
```

### 8.5 Configure SQL Azure AD Authentication

```bash
# Set Azure AD admin (use your user account)
MY_USER_ID=$(az ad signed-in-user show --query id -o tsv)

az sql server ad-admin create \
  --resource-group $AZURE_RESOURCE_GROUP \
  --server-name $AZURE_SQL_SERVER_NAME \
  --display-name "SQL Admin" \
  --object-id $MY_USER_ID
```

---

## Step 9: Initialize Search Index

### 9.1 Get Function App URL

```bash
FUNCTION_URL=$(az functionapp show \
  --name $AZURE_FUNCTION_APP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --query defaultHostName -o tsv)

echo "Function URL: https://$FUNCTION_URL"
```

### 9.2 Create Search Index

```bash
curl -X POST "https://$FUNCTION_URL/api/create-index" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{"message": "Search index created successfully"}
```

---

## Step 10: Test Deployment

### 10.1 Health Check

```bash
curl "https://$FUNCTION_URL/api/health"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-25T10:00:00Z",
  "version": "1.0.0"
}
```

### 10.2 Upload Test Document

```bash
# Create a test PDF (or use your own)
az storage blob upload \
  --account-name $AZURE_STORAGE_ACCOUNT_NAME \
  --container-name raw-documents \
  --name test-document.pdf \
  --file /path/to/test.pdf \
  --auth-mode login
```

### 10.3 Monitor Processing

**Via Azure Portal:**
1. Navigate to Function App
2. Go to "Functions" → "process_oem_document"
3. Click "Monitor"
4. View execution logs

**Via CLI:**
```bash
az monitor app-insights query \
  --app $AZURE_APP_INSIGHTS_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --analytics-query "traces | where message contains 'Processing document' | order by timestamp desc | take 10"
```

### 10.4 Verify Output

```bash
# List processed documents
az storage blob list \
  --account-name $AZURE_STORAGE_ACCOUNT_NAME \
  --container-name processed-documents \
  --auth-mode login \
  --output table
```

---

## Step 11: Configure Monitoring

### 11.1 Create Alert Rules

```bash
# Alert on function failures
az monitor metrics alert create \
  --name "Function-Failures" \
  --resource-group $AZURE_RESOURCE_GROUP \
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Web/sites/$AZURE_FUNCTION_APP_NAME" \
  --condition "count FunctionExecutionCount where ResultType == 'Failed' > 5" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### 11.2 Configure Log Analytics

```bash
# Enable diagnostic settings
az monitor diagnostic-settings create \
  --name "function-diagnostics" \
  --resource "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Web/sites/$AZURE_FUNCTION_APP_NAME" \
  --logs '[{"category": "FunctionAppLogs", "enabled": true}]' \
  --metrics '[{"category": "AllMetrics", "enabled": true}]' \
  --workspace "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/$AZURE_APP_INSIGHTS_NAME"
```

---

## Step 12: Production Hardening

### 12.1 Enable Private Endpoints

```bash
# Create VNet
az network vnet create \
  --resource-group $AZURE_RESOURCE_GROUP \
  --name multimodal-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name default \
  --subnet-prefix 10.0.0.0/24
```

### 12.2 Configure Network Security

```bash
# Disable public access to storage
az storage account update \
  --name $AZURE_STORAGE_ACCOUNT_NAME \
  --resource-group $AZURE_RESOURCE_GROUP \
  --default-action Deny
```

### 12.3 Enable Backup

```bash
# Configure storage backup
az backup vault create \
  --resource-group $AZURE_RESOURCE_GROUP \
  --name backup-vault \
  --location $AZURE_LOCATION
```

---

## Troubleshooting

### Issue: Function deployment fails

**Solution:**
```bash
# Check function app logs
func azure functionapp logstream $AZURE_FUNCTION_APP_NAME
```

### Issue: Authentication errors

**Solution:**
```bash
# Verify managed identity
az functionapp identity show \
  --name $AZURE_FUNCTION_APP_NAME \
  --resource-group $AZURE_RESOURCE_GROUP

# Check role assignments
az role assignment list --assignee $FUNCTION_IDENTITY
```

### Issue: Database connection fails

**Solution:**
```bash
# Check firewall rules
az sql server firewall-rule list \
  --resource-group $AZURE_RESOURCE_GROUP \
  --server $AZURE_SQL_SERVER_NAME
```

---

## Post-Deployment Checklist

- [ ] All Azure resources created successfully
- [ ] Database migrations completed
- [ ] Function app deployed and running
- [ ] RBAC permissions configured
- [ ] Search index created
- [ ] Test document processed successfully
- [ ] Monitoring alerts configured
- [ ] Documentation reviewed

---

## Next Steps

1. **Upload Production Documents**: Start processing real OEM documents
2. **Monitor Performance**: Review Application Insights dashboards
3. **Optimize Costs**: Analyze cost logs and adjust resources
4. **Scale as Needed**: Upgrade to Premium plan if required
5. **Regular Maintenance**: Follow maintenance schedule in ARCHITECTURE.md

---

**Deployment Complete! 🎉**

For support, refer to README.md or create an issue in the repository.
