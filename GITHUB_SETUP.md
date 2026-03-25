# 📤 GitHub Upload Guide

Step-by-step instructions to upload this project to GitHub.

---

## Prerequisites

- Git installed (`git --version`)
- GitHub account created
- Git configured with your credentials

---

## Quick Setup (Recommended)

### Step 1: Initialize Git Repository

```bash
cd c:\Users\surso\CascadeProjects\Azure_Information_Extraction
git init
```

### Step 2: Add All Files

```bash
git add .
```

### Step 3: Create Initial Commit

```bash
git commit -m "Initial commit: Enterprise Multimodal RAG Pipeline

- Azure AD authentication with Managed Identity
- Centralized logging (Application Insights + SQL Database)
- Document processing pipeline (OCR, chunking, extraction)
- Hybrid search with Azure AI Search
- RAGAS evaluation framework
- Production-grade code with tests
- Comprehensive documentation"
```

### Step 4: Create GitHub Repository

**Option A: Via GitHub Web Interface**
1. Go to https://github.com/new
2. Repository name: `azure-multimodal-rag-pipeline` (or your choice)
3. Description: `Enterprise-grade multimodal RAG system for OEM document processing with Azure AD security, centralized logging, and automated evaluation`
4. Choose Public or Private
5. **DO NOT** initialize with README (we already have one)
6. Click "Create repository"

**Option B: Via GitHub CLI** (if installed)
```bash
gh repo create azure-multimodal-rag-pipeline --public --source=. --remote=origin --push
```

### Step 5: Connect to GitHub Repository

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline.git
```

### Step 6: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

---

## Verify Upload

After pushing, verify on GitHub:
- ✅ All files are present
- ✅ README.md displays correctly
- ✅ .gitignore is working (no .env, venv, etc.)

---

## Add GitHub Repository Badges

After creating the repo, update README.md with your actual repository URL:

```markdown
[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?style=flat&logo=github)](https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline)
[![Stars](https://img.shields.io/github/stars/YOUR_USERNAME/azure-multimodal-rag-pipeline?style=social)](https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline/stargazers)
```

---

## Troubleshooting

### Issue: Git not initialized
```bash
git init
```

### Issue: Remote already exists
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline.git
```

### Issue: Authentication failed
```bash
# Use GitHub Personal Access Token
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline.git
```

Or configure Git credentials:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Issue: Large files rejected
GitHub has a 100MB file size limit. Check for large files:
```bash
find . -type f -size +50M
```

---

## Optional: Create .github Folder

Add GitHub-specific configurations:

### GitHub Actions Workflow (CI/CD)
Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src
```

### Issue Templates
Create `.github/ISSUE_TEMPLATE/bug_report.md`

### Pull Request Template
Create `.github/PULL_REQUEST_TEMPLATE.md`

---

## Post-Upload Checklist

- [ ] Repository created on GitHub
- [ ] All files pushed successfully
- [ ] README.md displays correctly
- [ ] .gitignore working (no sensitive files)
- [ ] Repository description added
- [ ] Topics/tags added (azure, rag, ai, openai, etc.)
- [ ] License file present (MIT)
- [ ] Documentation complete

---

## Sharing Your Repository

Once uploaded, share with:
- Repository URL: `https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline`
- Clone command: `git clone https://github.com/YOUR_USERNAME/azure-multimodal-rag-pipeline.git`

---

## Maintaining the Repository

### Making Updates
```bash
git add .
git commit -m "Description of changes"
git push origin main
```

### Creating Releases
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

---

**Ready to upload!** Follow the steps above to get your project on GitHub. 🚀
