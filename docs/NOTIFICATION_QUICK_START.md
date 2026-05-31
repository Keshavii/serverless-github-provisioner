# Notification System - Quick Start Guide

## 🎯 Overview

Add SNS + Slack notifications to **both error handlers** (GitHub Handler + Webhook Handler) plus DLQ.

**Total Integration Points:** 12 notifications across 3 Lambda functions

---

## 📦 What We've Created

### ✅ Files Created
1. **`src/notifications.py`** - Complete notification module with 8 helper functions
2. **`docs/NOTIFICATION_INTEGRATION_GUIDE.md`** - Detailed line-by-line integration instructions

---

## ⚡ Quick Implementation Steps

### **Step 1: Infrastructure** (Terraform)

Create SNS topic and configure environment variables:

```bash
# Create infra/modules/notifications/sns.tf (see full guide)
# Update infra/main.tf to include notifications module
# Add variables for alert_email and slack_webhook_url

terraform plan
terraform apply
```

### **Step 2: Code Changes** (3 files to modify)

#### A. **webhook_handler.py** - 4 notification points
```python
# Line 13: Add import
from .notifications import notify_webhook_error

# Add notifications at:
# - Line 104: Validation failure
# - Line 145: SQS send failure  
# - Line 190: JSON parse error
# - Line 220: General exception
```

#### B. **github_handler.py** - 6 notification points
```python
# Line 13: Add imports
from .notifications import (
    notify_repo_created,
    notify_validation_error,
    notify_github_error,
    notify_permission_error,
    notify_jira_error,
    notify_webhook_error
)

# Add notifications at:
# - Line 310: Success (after JIRA update)
# - Line 327: Validation error
# - Line 371: GitHub permission/permanent errors
# - Line 410: JIRA permanent error
# - Line 426: General exception
```

#### C. **dlq_handler.py** - 1 notification point
```python
# Line 8: Add import
from .notifications import notify_dlq_alert

# Add notification at:
# - Line 117: After JIRA update succeeds
```

### **Step 3: Dependencies**

Add to `requirements-lambda.txt`:
```txt
requests==2.31.0
```

Rebuild Lambda layer:
```bash
cd infra
./build_lambda_layer.sh
```

### **Step 4: Secrets Configuration**

Store Slack webhook in Secrets Manager:
```bash
aws secretsmanager create-secret \
    --name github-automation/slack-config \
    --secret-string '{"slack_webhook_url":"https://hooks.slack.com/services/YOUR/WEBHOOK"}'
```

### **Step 5: Environment Variables**

Update Lambda environment configuration (Terraform or Console):
```bash
SNS_ALERT_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:github-automation-alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### **Step 6: Deploy**

```bash
cd infra/environment/dev
terraform apply
```

### **Step 7: Test**

```bash
# Test DLQ alert
aws sqs send-message \
    --queue-url $(terraform output -raw dlq_url) \
    --message-body '{
      "ticket_id": "TEST-123",
      "repo_name": "test-repo",
      "github_org": "hiyamodi"
    }'

# Check Slack channel for alert
```

---

## 📋 Notification Points Summary

| Lambda | Scenario | Function | Severity | Line# |
|--------|----------|----------|----------|-------|
| **Webhook** | SQS Failure | `notify_webhook_error()` | ERROR | ~145 |
| **Webhook** | Validation Fail | `notify_webhook_error()` | ERROR | ~104 |
| **Webhook** | JSON Error | `notify_webhook_error()` | ERROR | ~190 |
| **Webhook** | Exception | `notify_webhook_error()` | ERROR | ~220 |
| **GitHub** | Success ✅ | `notify_repo_created()` | INFO | ~310 |
| **GitHub** | Validation | `notify_validation_error()` | WARNING | ~327 |
| **GitHub** | Permission | `notify_permission_error()` | CRITICAL | ~371 |
| **GitHub** | GitHub Error | `notify_github_error()` | ERROR | ~371 |
| **GitHub** | JIRA Error | `notify_jira_error()` | ERROR | ~410 |
| **GitHub** | Exception | `notify_webhook_error()` | ERROR | ~426 |
| **DLQ** | Max Retries | `notify_dlq_alert()` | CRITICAL | ~117 |

**Total:** 11 notifications (1 success, 10 errors)

---

## 🔍 What Gets Notified

### ✅ **Success Notifications** (INFO)
- Repository created successfully
- JIRA ticket updated with repo URL

### ⚠️ **Warning Notifications** (WARNING)  
- Validation errors (user input problems)

### ❌ **Error Notifications** (ERROR)
- GitHub API errors (permanent)
- JIRA API errors (permanent)
- Webhook processing failures
- SQS queue failures

### 🚨 **Critical Notifications** (CRITICAL)
- GitHub permission/auth errors
- DLQ alerts (failed after 3 retries)

---

## 🧪 Testing Scenarios

1. **Success:** Create valid JIRA ticket → Slack shows ✅ green success
2. **Validation:** Create ticket with invalid repo name → Slack shows ⚠️ orange warning
3. **Permission:** Use invalid GitHub credentials → Slack shows 🔒 red critical
4. **DLQ:** Force 3 failures → Slack shows 🚨 red critical

---

## 📊 Expected Slack Output

**Success:**
```
✅ Repository Created: my-repo
Successfully created repository `my-repo` in organization `hiyamodi`
```

**Error:**
```
❌ GitHub Error: my-repo
GitHub API error for `my-repo`:
Repository already exists
```

**Critical:**
```
🚨 DLQ Alert: Repository Creation Failed After Retries
*CRITICAL:* Message moved to Dead Letter Queue
```

---

## 📚 Full Documentation

See **`docs/NOTIFICATION_INTEGRATION_GUIDE.md`** for:
- Line-by-line code examples
- Complete Terraform configuration
- Detailed testing procedures
- Infrastructure setup
- IAM permissions
- CloudWatch alarms

---

## ⏱️ Estimated Time

- **Infrastructure Setup:** 1 hour
- **Code Integration:** 1-2 hours  
- **Testing:** 30 minutes
- **Total:** 3-4 hours

---

## ✅ Completion Checklist

- [ ] `src/notifications.py` created
- [ ] Terraform notifications module created
- [ ] 4 notifications added to `webhook_handler.py`
- [ ] 6 notifications added to `github_handler.py`
- [ ] 1 notification added to `dlq_handler.py`
- [ ] `requests` added to requirements
- [ ] Lambda layer rebuilt
- [ ] Slack webhook obtained
- [ ] SNS topic created
- [ ] Environment variables configured
- [ ] Infrastructure deployed
- [ ] End-to-end test completed
- [ ] Slack channel shows notifications

---

## 🎉 Result

After implementation, you'll have **real-time notifications** for:
- ✅ Every successful repository creation
- ❌ Every error that requires attention
- 🚨 Every critical failure (DLQ, permissions)

All notifications go to **both**:
- 📧 Email (via SNS)
- 💬 Slack channel (direct webhook)
