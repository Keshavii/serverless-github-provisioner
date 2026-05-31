# 📦 AWS Resources Inventory - GitHub Repository Automation

Complete inventory of all deployed AWS resources in the **test** environment.

---

## 📊 Resource Summary

| Resource Type | Count | Status |
|--------------|-------|--------|
| **Lambda Functions** | 3 | ✅ Deployed |
| **SQS Queues** | 2 | ✅ Active |
| **Secrets Manager** | 2 | ✅ Configured |
| **SNS Topics** | 1 | ✅ Active |
| **IAM Roles** | 3 | ✅ Active |
| **Lambda Layers** | 1 | ✅ Active |
| **CloudWatch Alarms** | 0 | ⚠️ Not configured |
| **Total Terraform Resources** | 10 | ✅ Managed |

---

## 🔧 Lambda Functions (3)

### 1. **Webhook Handler**
```
Name:     github-repo-automation-test-webhook-handler
Runtime:  python3.9
Handler:  src.webhook_handler.lambda_handler
Memory:   512 MB
Timeout:  60 seconds
Updated:  2026-04-30 08:43:07 UTC
```
**Purpose:** Receives JIRA webhooks and validates/queues repository creation requests

### 2. **Repository Creator**
```
Name:     github-repo-automation-test-repo-creator
Runtime:  python3.9
Handler:  src.github_handler.lambda_handler
Memory:   512 MB
Timeout:  300 seconds (5 minutes)
Updated:  2026-04-22 10:57:41 UTC
```
**Purpose:** Processes SQS messages and creates GitHub repositories

### 3. **DLQ Handler**
```
Name:     github-repo-automation-test-dlq-handler
Runtime:  python3.9
Handler:  src.dlq_handler.lambda_handler
Memory:   512 MB
Timeout:  60 seconds
Updated:  2026-04-22 10:57:34 UTC
```
**Purpose:** Processes failed messages from Dead Letter Queue

---

## 🔐 Secrets Manager (2)

### 1. **GitHub Credentials**
```
Name:        github-repo-automation/github
Description: GitHub App credentials for repository automation
Updated:     2026-04-22 14:04:43 IST
```
**Contains:**
- `app_id` - GitHub App ID
- `private_key` - GitHub App private key (RSA)

### 2. **JIRA Credentials**
```
Name:        github-repo-automation/jira
Description: JIRA credentials for repository automation
Updated:     2026-04-22 14:04:41 IST
```
**Contains:**
- `url` - JIRA instance URL
- `email` - JIRA user email
- `token` - JIRA API token

---

## 📬 SQS Queues (2)

### 1. **Main Queue**
```
URL: https://sqs.us-east-1.amazonaws.com/521464398395/github-repo-automation-test-queue
```
**Purpose:** Primary queue for repository creation requests
**Consumers:** `github-repo-automation-test-repo-creator`

### 2. **Dead Letter Queue (DLQ)**
```
URL: https://sqs.us-east-1.amazonaws.com/521464398395/github-repo-automation-test-dlq
```
**Purpose:** Stores failed messages after 3 retry attempts
**Consumers:** `github-repo-automation-test-dlq-handler`

---

## 🔔 SNS Topics (1)

### **Alerts Topic**
```
ARN: arn:aws:sns:us-east-1:521464398395:github-repo-automation-test-alerts
```
**Purpose:** Distributes notifications for errors and alerts
**Subscriptions:**
- Email: hiya.modi.here@gmail.com
- Slack: https://hooks.slack.com/services/T065DVAH2ER/B0B0Y1YHBN0/...

---

## 👤 IAM Roles (3)

### 1. **Webhook Handler Role**
```
Name: github-repo-automation-test-webhook-handler-role
```
**Permissions:**
- Write to SQS queue
- Read from Secrets Manager
- CloudWatch Logs
- SNS Publish (conditional)

### 2. **Repository Creator Role**
```
Name: github-repo-automation-test-repo-creator-role
```
**Permissions:**
- Read from SQS queue
- Read from Secrets Manager
- CloudWatch Logs
- SNS Publish (conditional)

### 3. **DLQ Handler Role**
```
Name: github-repo-automation-test-dlq-handler-role
```
**Permissions:**
- Read from DLQ
- Read from Secrets Manager
- CloudWatch Logs
- SNS Publish (conditional)

---

## 📦 Lambda Layer (1)

### **Dependencies Layer**
```
Name: github-repo-automation-test-dependencies
```
**Contains:**
- PyGithub==2.1.1
- jira==3.5.2
- requests==2.31.0
- pydantic==2.5.3
- structlog==23.2.0
- cryptography>=41.0.0
- Other dependencies from requirements-lambda.txt

---

## 🔗 Resource Relationships

```
JIRA Webhook
    ↓
[Webhook Handler Lambda]
    ↓
[SQS Main Queue] ─┐
    ↓             │ (3 retries)
[Repo Creator]    │
    ↓             │
GitHub API        │
    ↓             ↓
Success/Fail  [DLQ] → [DLQ Handler Lambda]
    ↓             ↓
JIRA Update   [SNS Topic] → Email + Slack
```

---

## 📍 AWS Region

**Primary Region:** `us-east-1` (US East - N. Virginia)

---

## 🔍 Quick Commands

### View Lambda Logs
```bash
# Webhook Handler
aws logs tail /aws/lambda/github-repo-automation-test-webhook-handler --follow

# Repo Creator  
aws logs tail /aws/lambda/github-repo-automation-test-repo-creator --follow

# DLQ Handler
aws logs tail /aws/lambda/github-repo-automation-test-dlq-handler --follow
```

### Check Queue Status
```bash
# Main queue
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/521464398395/github-repo-automation-test-queue \
  --attribute-names All

# DLQ
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/521464398395/github-repo-automation-test-dlq \
  --attribute-names All
```

---

**Last Updated:** 2026-04-30
**Environment:** test
**Terraform State:** 10 resources managed
