# Webhook Failure Handling

## Overview

The system now automatically updates JIRA tickets when webhook validation or processing fails in Lambda1 (`webhook_handler.py`). This ensures users receive immediate feedback when something goes wrong, preventing "silent failures" where tickets sit unprocessed.

## Architecture

```
JIRA Webhook → Lambda1 (webhook_handler.py)
                    ↓
                 Validation
                    ↓
            ┌──────┴──────┐
            │             │
         Success       Failure
            │             │
            ↓             ↓
      Push to SQS    Update JIRA
                   (Comment + Transition)
```

## Failure Scenarios

Lambda1 updates JIRA tickets in these failure scenarios:

### 1. **Webhook Validation Failure**
- **Trigger**: Invalid webhook payload structure
- **Error Type**: "Webhook Validation Error"
- **Message**: "The webhook payload structure is invalid or missing required fields."

### 2. **JSON Parsing Error**
- **Trigger**: Malformed JSON in webhook body
- **Error Type**: "JSON Parsing Error"
- **Message**: "Failed to parse webhook payload: {error details}"

### 3. **SQS Queue Error**
- **Trigger**: Failed to send message to SQS queue
- **Error Type**: "SQS Queue Error"
- **Message**: "Failed to queue message for processing: {error details}"

### 4. **Internal Server Error**
- **Trigger**: Unexpected exceptions in Lambda1
- **Error Type**: "Internal Server Error"
- **Message**: "Unexpected error during webhook processing: {error details}"

## JIRA Updates

When a failure occurs, the system:

1. **Adds a Comment** with:
   - Error type and message
   - Correlation ID for debugging
   - Action required instructions

2. **Adds Labels**:
   - `webhook-validation-failed`
   - `automated`
   - `requires-manual-review`

3. **Transitions Ticket** (if enabled):
   - Target Status: "Manual Review" (configurable)
   - Resolution: None (configurable)

## Configuration

Configure webhook failure handling in `.env`:

```bash
# Webhook validation failure transition (for Lambda1 failures)
AUTO_TRANSITION_ON_WEBHOOK_FAILURE=true
WEBHOOK_FAILURE_TRANSITION_NAME=Manual Review
WEBHOOK_FAILURE_RESOLUTION=
```

### Settings Explained

- **AUTO_TRANSITION_ON_WEBHOOK_FAILURE**: Enable/disable automatic transition on webhook failures
- **WEBHOOK_FAILURE_TRANSITION_NAME**: Target status for failed webhooks (e.g., "Manual Review", "To Do", "Backlog")
- **WEBHOOK_FAILURE_RESOLUTION**: Resolution to set (leave empty if not required by your JIRA workflow)

## Example JIRA Comment

```
❌ Webhook Processing Failed

Error Type: SQS Queue Error
Error Message: Failed to queue message for processing: Access denied to SQS queue

Correlation ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

---
Action Required:
Please review the ticket details and resubmit or contact support.

This is an automated message from the GitHub Repository Creation System.
```

## Testing

Test the webhook failure handling:

```bash
python test_webhook_failure.py RELB-7452
```

This will:
1. Simulate a webhook validation failure
2. Add a test comment to the JIRA ticket
3. Add failure labels
4. Transition to Manual Review (if enabled)

## Best Practices

1. **Enable Auto-Transition**: Set `AUTO_TRANSITION_ON_WEBHOOK_FAILURE=true` to ensure failed tickets don't sit unprocessed
2. **Use Manual Review Status**: Create a "Manual Review" status in your JIRA workflow for failed automations
3. **Monitor Logs**: Check CloudWatch logs for correlation IDs when investigating failures
4. **Review Regularly**: Set up filters in JIRA to review tickets with `webhook-validation-failed` label

## Comparison: Lambda1 vs Lambda2 Failures

| Aspect | Lambda1 (Webhook) | Lambda2 (Repo Creation) |
|--------|------------------|------------------------|
| **Config** | `AUTO_TRANSITION_ON_WEBHOOK_FAILURE` | `AUTO_TRANSITION_ON_FAILURE` |
| **Status** | Manual Review | Manual Review |
| **Labels** | `webhook-validation-failed` | `repository-creation-failed` |
| **When** | Validation/Queue errors | GitHub API errors |

## Troubleshooting

### Ticket Not Transitioning

1. **Check Configuration**:
   ```bash
   grep AUTO_TRANSITION_ON_WEBHOOK_FAILURE .env
   ```

2. **Verify Transition Name**:
   - Log into JIRA
   - View ticket workflow
   - Ensure "Manual Review" status exists and is accessible from current status

3. **Check Logs**:
   - Look for `webhook_transition_not_found` events
   - Review available transitions in log output

### Comment Not Added

1. **Verify JIRA Credentials**:
   ```bash
   grep JIRA_API_TOKEN .env
   ```

2. **Check Permissions**:
   - Ensure JIRA user has permission to comment on tickets
   - Verify user can edit ticket labels

## Related Documentation

- [Architecture](ARCHITECTURE_FINAL.md)
- [JIRA Client Testing](JIRA_CLIENT_TESTING.md)
- [AWS Serverless Setup](AWS_SERVERLESS_SETUP_GUIDE.md)

