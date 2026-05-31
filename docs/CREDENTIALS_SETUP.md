# 🔐 Credentials Setup Guide

Complete guide for setting up credentials for both **local development** and **AWS Lambda** deployment.

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Local Development Setup](#local-development-setup)
3. [AWS Lambda Setup](#aws-lambda-setup)
4. [GitHub App Setup](#github-app-setup)
5. [JIRA API Token Setup](#jira-api-token-setup)
6. [Verification](#verification)

---

## 🎯 **Overview**

The system supports **two authentication modes**:

| Mode | GitHub Auth | JIRA Auth | Configuration |
|------|-------------|-----------|---------------|
| **Local Development** | GitHub App (via `.env`) | API Token (via `.env`) | `.env` file |
| **AWS Lambda** | GitHub App (via Secrets Manager) | API Token (via Secrets Manager) | AWS Secrets Manager |

---

## 💻 **Local Development Setup**

### **Step 1: Create `.env` File**

Copy the example file:
```bash
cd github-repo-auto/Github-Auto-Repo-Creation
cp .env.example .env
```

### **Step 2: Configure GitHub App Credentials**

Edit `.env` and add your GitHub App credentials:

```bash
# GitHub App Configuration
GITHUB_APP_ID=3226611
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...your full private key content...
-----END RSA PRIVATE KEY-----
```

**Where to find these:**
- **App ID**: GitHub → Settings → Developer settings → GitHub Apps → Your App → App ID
- **Private Key**: GitHub → Settings → Developer settings → GitHub Apps → Your App → Generate private key (.pem file)

**Note:** You can paste the entire PEM file content directly into the `.env` file (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)

### **Step 3: Configure JIRA Credentials**

Add JIRA credentials to `.env`:

```bash
# JIRA Configuration
JIRA_URL=https://hiyamodi.atlassian.net
JIRA_EMAIL=hiya.modi.here@gmail.com
JIRA_API_TOKEN=your_jira_api_token_here
```

**Where to get JIRA API token:**
1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token to `.env`

### **Step 4: Configure Optional Settings**

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment
ENVIRONMENT=development
```

---

## ☁️ **AWS Lambda Setup**

### **Step 1: Create GitHub App Secret**

Store GitHub App credentials in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name github-repo-automation/github \
  --description "GitHub App credentials for repository automation" \
  --secret-string '{
    "GITHUB_APP_ID": "3226611",
    "GITHUB_APP_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
  }' \
  --region us-east-1
```

**Important:** 
- Replace newlines in the private key with `\n`
- Ensure the JSON is valid
- Keep the `-----BEGIN` and `-----END` markers

**Alternative: Using AWS Console**

1. Go to **AWS Secrets Manager** → **Store a new secret**
2. **Secret type:** Other type of secret
3. **Key-value pairs:**
   - Key: `GITHUB_APP_ID`, Value: `3226611`
   - Key: `GITHUB_APP_PRIVATE_KEY`, Value: `<paste full PEM content>`
4. **Secret name:** `github-repo-automation/github`
5. Click **Store**

### **Step 2: Create JIRA Secret**

```bash
aws secretsmanager create-secret \
  --name github-repo-automation/jira \
  --description "JIRA API credentials for repository automation" \
  --secret-string '{
    "JIRA_URL": "https://hiyamodi.atlassian.net",
    "JIRA_EMAIL": "hiya.modi.here@gmail.com",
    "JIRA_API_TOKEN": "your_jira_api_token_here"
  }' \
  --region us-east-1
```

### **Step 3: Grant Lambda IAM Permissions**

Ensure your Lambda function's IAM role has permission to read secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:github-repo-automation/*"
      ]
    }
  ]
}
```

---

## 🚀 **GitHub App Setup**

### **Create GitHub App (One-time setup)**

1. Go to: https://github.com/organizations/hiyamodi-devops-poc/settings/apps/new
2. **App name:** `Repo Creation Automation`
3. **Homepage URL:** `https://github.com/hiyamodi-devops-poc`
4. **Webhook:** Uncheck "Active" (not needed)
5. **Permissions:**
   - Repository permissions → Administration: **Read & Write**
   - Repository permissions → Contents: **Read & Write**
   - Repository permissions → Metadata: **Read-only**
   - Organization permissions → Administration: **Read-only**
6. **Where can this GitHub App be installed:** Only on this account
7. Click **Create GitHub App**
8. **Generate private key** → Download the `.pem` file
9. Note the **App ID**

### **Install GitHub App in Organization**

1. Go to: https://github.com/organizations/hiyamodi-devops-poc/settings/installations
2. Click on your app → **Install**
3. Select **All repositories** or specific repositories
4. Click **Install**
5. Note the **Installation ID** from the URL

---

## 🎫 **JIRA API Token Setup**

1. Log in to JIRA: https://hiyamodi.atlassian.net
2. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
3. Click **Create API token**
4. Enter a label: `GitHub Repo Automation`
5. Click **Create**
6. **Copy** the token (you won't see it again!)
7. Add to `.env` (local) or AWS Secrets Manager (Lambda)

---

## ✅ **Verification**

### **Local Development**

Test credentials work:

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Check GitHub App credentials
print('✅ GITHUB_APP_ID:', os.getenv('GITHUB_APP_ID'))
print('✅ GITHUB_APP_PRIVATE_KEY length:', len(os.getenv('GITHUB_APP_PRIVATE_KEY', '')))

# Check JIRA credentials
print('✅ JIRA_URL:', os.getenv('JIRA_URL'))
print('✅ JIRA_EMAIL:', os.getenv('JIRA_EMAIL'))
print('✅ JIRA_API_TOKEN length:', len(os.getenv('JIRA_API_TOKEN', '')))
"
```

### **AWS Lambda**

Verify secrets are loaded:

```bash
# Check GitHub secret
aws secretsmanager get-secret-value \
  --secret-id github-repo-automation/github \
  --region us-east-1 \
  --query SecretString \
  --output text

# Check JIRA secret
aws secretsmanager get-secret-value \
  --secret-id github-repo-automation/jira \
  --region us-east-1 \
  --query SecretString \
  --output text
```

---

## 🔄 **How It Works**

### **Local Development Flow**

```
1. Load .env file
   ↓
2. Environment variables set
   ↓
3. github_client.py reads GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY
   ↓
4. Creates GithubIntegration with App credentials
   ↓
5. Exchanges for Installation Access Token
   ↓
6. Authenticates API calls
```

### **AWS Lambda Flow**

```
1. Lambda invoked
   ↓
2. lambda_handler._load_secrets_to_env() called
   ↓
3. Reads from AWS Secrets Manager:
   - github-repo-automation/github
   - github-repo-automation/jira
   ↓
4. Sets environment variables
   ↓
5. github_client.py reads GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY
   ↓
6. Creates GithubIntegration with App credentials
   ↓
7. Exchanges for Installation Access Token
   ↓
8. Authenticates API calls
```

**✅ Same code works in both environments!**

---

## 🛡️ **Security Best Practices**

### **Local Development**

1. ✅ **Never commit `.env` file** to version control
2. ✅ `.env` is in `.gitignore`
3. ✅ Use `.env.example` as template
4. ✅ Keep `.env` permissions restricted: `chmod 600 .env`
5. ✅ Rotate credentials regularly

### **AWS Lambda**

1. ✅ **Use AWS Secrets Manager** (not environment variables)
2. ✅ Enable **automatic secret rotation** (optional)
3. ✅ Restrict IAM permissions to specific secrets
4. ✅ Enable **CloudTrail** for secret access auditing
5. ✅ Use **VPC endpoints** for Secrets Manager (optional)

---

## 🔧 **Troubleshooting**

### **Error: "GitHub App credentials not configured"**

**Local:**
- Check `.env` file exists
- Verify `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` are set
- Ensure private key includes `-----BEGIN` and `-----END` markers
- Try loading `.env` manually: `from dotenv import load_dotenv; load_dotenv()`

**Lambda:**
- Check AWS Secrets Manager secret exists: `github-repo-automation/github`
- Verify secret contains `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` keys
- Check Lambda IAM role has `secretsmanager:GetSecretValue` permission
- Review CloudWatch Logs for "secrets_loading_error"

### **Error: "GitHub App is not installed in organization"**

1. Go to: https://github.com/organizations/hiyamodi-devops-poc/settings/installations
2. Check if app is installed
3. If not, install the app
4. If installed, verify organization name matches exactly

### **Error: "403 Forbidden" from GitHub API**

1. Verify GitHub App has correct permissions:
   - Repository → Administration: Read & Write
   - Organization → Administration: Read-only
2. Re-install the app to refresh permissions
3. Check if Installation Access Token is being generated correctly

### **Error: "JIRA authentication failed"**

1. Verify JIRA URL is correct: `https://hiyamodi.atlassian.net`
2. Check email matches your Atlassian account
3. Regenerate API token if needed
4. Test token with curl:
   ```bash
   curl -u hiya.modi.here@gmail.com:your-api-token \
     https://hiyamodi.atlassian.net/rest/api/2/myself
   ```

---

## 📚 **Additional Resources**

- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [JIRA API Tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)

---

## 🎉 **Summary**

| Environment | GitHub Credentials | JIRA Credentials | Config Location |
|-------------|-------------------|------------------|-----------------|
| **Local** | `.env` file | `.env` file | `.env` |
| **Lambda** | AWS Secrets Manager | AWS Secrets Manager | `github-repo-automation/*` |

**Both environments use the same code!** The only difference is where credentials are loaded from. 🚀


