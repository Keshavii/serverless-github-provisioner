# Notification Integration Guide

Complete guide showing exactly where to add SNS + Slack notifications in both Lambda handlers.

---

## 📋 Summary of Integration Points

| Handler | Notification Type | Severity | Trigger Point | Function to Call |
|---------|------------------|----------|---------------|------------------|
| **Webhook Handler** | | | | |
| | SQS Send Failure | ERROR | Line 135-145 | `notify_webhook_error()` |
| | Validation Failure | ERROR | Line 97-104 | `notify_webhook_error()` |
| | JSON Parse Error | ERROR | Line 164-191 | `notify_webhook_error()` |
| | General Exception | ERROR | Line 193-221 | `notify_webhook_error()` |
| **GitHub Handler** | | | | |
| | Success | INFO | Line 310 (after JIRA update) | `notify_repo_created()` |
| | Validation Error | WARNING | Line 316-331 | `notify_validation_error()` |
| | GitHub Permission Error | CRITICAL | Line 333-375 (when category="permission") | `notify_permission_error()` |
| | GitHub Permanent Error | ERROR | Line 333-375 (when category!="permission") | `notify_github_error()` |
| | JIRA Permanent Error | ERROR | Line 377-431 (when not retryable) | `notify_jira_error()` |
| | General Exception | ERROR | Line 413-431 | `notify_webhook_error()` |
| **DLQ Handler** | | | | |
| | DLQ Alert | CRITICAL | Line 105-118 (after JIRA update) | `notify_dlq_alert()` |

**Total: 12 notification points**

---

## 🔧 Integration Instructions

### **Step 1: Import notification functions at the top of each file**

#### `src/webhook_handler.py` - Add at line 13:
```python
from .notifications import notify_webhook_error
```

#### `src/github_handler.py` - Add at line 13:
```python
from .notifications import (
    notify_repo_created,
    notify_validation_error,
    notify_github_error,
    notify_permission_error,
    notify_jira_error,
    notify_webhook_error
)
```

#### `src/dlq_handler.py` - Add at line 8:
```python
from .notifications import notify_dlq_alert
```

---

## 📍 Webhook Handler - 4 Notification Points

### **Point 1: SQS Send Failure** (Line ~145, after line 144)

**Location:** Inside `lambda_handler()` in the SQS error exception handler

**Add AFTER line 144:**
```python
# Add this notification call
notify_webhook_error(
    ticket_id=ticket_data.get('ticket_id', 'UNKNOWN'),
    error_type='SQS Send Failure',
    error_message=f"Failed to queue message to SQS: {str(sqs_error)}",
    correlation_id=correlation_id
)
```

**Context:** When message fails to send to SQS queue after webhook validation passed.

---

### **Point 2: Validation Failure** (Line ~104, after line 103)

**Location:** Inside `lambda_handler()` after validation fails

**Add AFTER line 103 (after JIRA update call):**
```python
# Add this notification call
notify_webhook_error(
    ticket_id=ticket_data.get('ticket_id', 'UNKNOWN'),
    error_type='Validation Error',
    error_message='Webhook payload validation failed. Check JIRA ticket for details.',
    correlation_id=correlation_id
)
```

**Context:** When webhook payload validation fails (missing fields, invalid data).

---

### **Point 3: JSON Parse Error** (Line ~190, after line 189)

**Location:** Inside `lambda_handler()` in JSON decode exception handler

**Add AFTER line 189 (after the try-except block that attempts JIRA update):**
```python
# Add this notification call (only if ticket_id was extracted)
if ticket_id:
    notify_webhook_error(
        ticket_id=ticket_id,
        error_type='JSON Parsing Error',
        error_message=f"Invalid JSON in webhook payload: {str(e)}",
        correlation_id=correlation_id
    )
```

**Context:** When webhook body contains invalid JSON.

---

### **Point 4: General Exception** (Line ~220, after line 219)

**Location:** Inside `lambda_handler()` in general exception handler

**Add AFTER line 219 (after the try-except block that attempts JIRA update):**
```python
# Add this notification call (only if ticket_id was extracted)
if ticket_id:
    notify_webhook_error(
        ticket_id=ticket_id,
        error_type='Internal Server Error',
        error_message=f"Unexpected error during webhook processing: {str(e)}",
        correlation_id=correlation_id
    )
```

**Context:** Any unexpected error during webhook processing.

---

## 📍 GitHub Handler - 6 Notification Points

### **Point 1: Success** (Line ~310-312, AFTER line 310)

**Location:** Inside `process_message()` after successful JIRA update

**Add AFTER line 310 (after `update_jira_success()` call):**
```python
# 🆕 Send success notification
notify_repo_created(
    ticket_id=ticket_id,
    repo_name=validated_data.repo_name,
    repo_url=repo_data.get('html_url'),
    github_org=validated_data.github_org,
    correlation_id=correlation_id
)
```

**Context:** Repository successfully created and JIRA ticket updated.

---

### **Point 2: Validation Error** (Line ~327-329, AFTER line 327)

**Location:** Inside `process_message()` in ValidationError exception handler

**Add AFTER line 327 (after `update_jira_failure()` call):**
```python
# 🆕 Send validation error notification
notify_validation_error(
    ticket_id=ticket_id,
    repo_name=message_data.get('repo_name', 'UNKNOWN'),
    github_org=message_data.get('github_org', 'UNKNOWN'),
    error_message=str(e),
    correlation_id=correlation_id
)
```

**Context:** Input validation failed (missing fields, invalid repo name, etc.).

---

### **Point 3: GitHub Permission/Auth Error** (Line ~365-371, AFTER line 371)

**Location:** Inside `process_message()` in GitHubAPIError handler, when `error_category == "permission"`

**Add AFTER line 371 (after `update_jira_failure()` call), but ONLY for permission errors:**

First, modify the existing code structure to handle permission errors specially:

```python
# Around line 356-375, replace with:
else:
    # PERMANENT ERRORS: Update JIRA immediately and don't retry
    log_and_monitor(
        "permanent_github_error",
        level="ERROR",
        correlation_id=correlation_id,
        ticket_id=ticket_id,
        error=str(e),
        error_category=error_category,
        status_code=e.status_code
    )

    # Build specific error message for user
    error_msg = _build_github_error_message(e, error_category)

    # Update JIRA with specific error details
    update_jira_failure(ticket_id, error_msg, correlation_id)

    # 🆕 Send notification based on error category
    if error_category == "permission":
        # CRITICAL: Permission errors need immediate attention
        notify_permission_error(
            ticket_id=ticket_id,
            repo_name=validated_data.repo_name,
            github_org=validated_data.github_org,
            error_message=error_msg,
            correlation_id=correlation_id
        )
    else:
        # Other permanent GitHub errors
        notify_github_error(
            ticket_id=ticket_id,
            repo_name=validated_data.repo_name,
            github_org=validated_data.github_org,
            error_message=error_msg,
            error_category=error_category,
            correlation_id=correlation_id
        )

    # Return True to delete message (no retry for permanent errors)
    return True
```

**Context:**
- **Permission errors (401/403):** GitHub App credentials invalid or insufficient permissions → CRITICAL
- **Other permanent errors:** Repository already exists, invalid config → ERROR

---

### **Point 4: JIRA Permanent Error** (Line ~400-410, AFTER line 410)

**Location:** Inside `process_message()` in JiraAPIError handler, when `e.is_retryable == False`

**Add AFTER line 410 (in the `else` block for non-retryable JIRA errors):**

```python
# Around line 395-411, replace the else block with:
else:
    # PERMANENT JIRA ERROR
    log_and_monitor(
        "permanent_jira_error",
        level="ERROR",
        correlation_id=correlation_id,
        ticket_id=ticket_id,
        error=str(e),
        status_code=e.status_code,
        message="JIRA API returned permanent error. Cannot update ticket."
    )

    # 🆕 Send notification for permanent JIRA errors
    notify_jira_error(
        ticket_id=ticket_id,
        repo_name=validated_data.repo_name if 'validated_data' in locals() else 'UNKNOWN',
        error_message=str(e),
        correlation_id=correlation_id
    )

    # DevOps needs to manually update JIRA or fix JIRA credentials
    return True
```

**Context:** JIRA API returned a permanent error (ticket doesn't exist, invalid credentials, etc.).

---

### **Point 5: General Exception** (Line ~426-428, AFTER line 426)

**Location:** Inside `process_message()` in the final general exception handler

**Add AFTER line 426 (after `update_jira_failure()` call):**

```python
# Around line 425-431, replace with:
try:
    update_jira_failure(ticket_id, str(e), correlation_id)

    # 🆕 Send notification for unexpected errors
    notify_webhook_error(
        ticket_id=ticket_id,
        error_type='Unexpected Error',
        error_message=f"Unknown error during repository creation: {str(e)}",
        correlation_id=correlation_id
    )
except Exception:
    pass  # Best effort

# Retry on unknown errors
return False
```

**Context:** Unexpected exception that doesn't match known error types.

---

## 📍 DLQ Handler - 1 Notification Point

### **Point 1: DLQ Alert** (Line ~118, AFTER line 117)

**Location:** Inside `_process_dlq_message()` after JIRA update succeeds

**Add AFTER line 117 (after the log_and_monitor success call):**

```python
# Around line 112-118, add after the log_and_monitor call:
log_and_monitor(
    "dlq_jira_update_success",
    level="INFO",
    correlation_id=correlation_id,
    ticket_id=ticket_id
)

# 🆕 Send critical DLQ alert
notify_dlq_alert(
    ticket_id=ticket_id,
    repo_name=repo_name,
    github_org=github_org,
    error_summary=error_summary,
    correlation_id=correlation_id
)
```

**Context:** Message reached DLQ after all retry attempts failed → CRITICAL alert needed.

---

## 🧪 Testing Each Notification Point

### Test 1: Validation Error
```python
# Trigger: Create JIRA ticket with missing required field
# Expected: notify_validation_error() called
# Severity: WARNING
```

### Test 2: GitHub Permission Error
```python
# Trigger: Use invalid GitHub App credentials
# Expected: notify_permission_error() called
# Severity: CRITICAL
```

### Test 3: Webhook JSON Error
```python
# Trigger: Send malformed JSON to webhook
# Expected: notify_webhook_error() called
# Severity: ERROR
```

### Test 4: Success
```python
# Trigger: Create valid JIRA ticket → repo created
# Expected: notify_repo_created() called
# Severity: INFO
```

### Test 5: DLQ Alert
```python
# Trigger: Send message to DLQ manually
# Expected: notify_dlq_alert() called
# Severity: CRITICAL
```

---

## ✅ Implementation Checklist

- [ ] Create `src/notifications.py` with all functions
- [ ] Add imports to `src/webhook_handler.py`
- [ ] Add imports to `src/github_handler.py`
- [ ] Add imports to `src/dlq_handler.py`
- [ ] Add 4 notification calls in webhook_handler.py
- [ ] Add 5 notification calls in github_handler.py
- [ ] Add 1 notification call in dlq_handler.py
- [ ] Add `requests` to `requirements-lambda.txt`
- [ ] Update Lambda environment variables (SNS_ALERT_TOPIC_ARN, SLACK_WEBHOOK_URL)
- [ ] Deploy and test each notification point
- [ ] Verify Slack messages appear correctly
- [ ] Verify SNS emails are received

---

## 🎨 Expected Slack Message Format

### Success Notification
```
✅ Repository Created: my-new-repo

Successfully created repository `my-new-repo` in organization `hiyamodi`

JIRA Ticket: REPO-123
Repository: my-new-repo
Organization: hiyamodi
Repository URL: https://github.com/hiyamodi/my-new-repo
```

### Error Notification
```
❌ GitHub Error: my-new-repo

GitHub API error for `my-new-repo`:
```
Repository already exists in organization
```

JIRA Ticket: REPO-456
Repository: my-new-repo
Organization: hiyamodi
Error Type: GitHub-business_rule
```

### Critical DLQ Alert
```
🚨 DLQ Alert: Repository Creation Failed After Retries

*CRITICAL:* Message moved to Dead Letter Queue

❌ Repository Creation Failed After Multiple Retry Attempts...

JIRA Ticket: REPO-789
Repository: failed-repo
Organization: hiyamodi
Error Type: DLQ-MaxRetriesExceeded
```

---

## 📊 Notification Flow Diagram

```
JIRA Ticket Created
    ↓
Webhook Received
    ├─ ❌ Validation Error → notify_webhook_error() [WARNING]
    ├─ ❌ JSON Error → notify_webhook_error() [ERROR]
    ├─ ❌ SQS Failure → notify_webhook_error() [ERROR]
    └─ ✅ Valid → Message to SQS
        ↓
    Repository Creator Lambda
        ├─ ❌ Validation Error → notify_validation_error() [WARNING]
        ├─ ❌ GitHub Permission → notify_permission_error() [CRITICAL]
        ├─ ❌ GitHub Error → notify_github_error() [ERROR]
        ├─ ❌ JIRA Error → notify_jira_error() [ERROR]
        ├─ 🔄 Transient Error → Retry (no notification)
        └─ ✅ Success → notify_repo_created() [INFO]
            ↓
        Failed After 3 Retries → DLQ
            ↓
        DLQ Handler → notify_dlq_alert() [CRITICAL]
```

---

## 🔐 Environment Variables Required

Add to Lambda environment configuration:

```bash
# SNS Topic ARN (from Terraform output)
SNS_ALERT_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:github-automation-alerts

# Slack Webhook URL (from AWS Secrets Manager or direct)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Note:** Store SLACK_WEBHOOK_URL in AWS Secrets Manager for production.
