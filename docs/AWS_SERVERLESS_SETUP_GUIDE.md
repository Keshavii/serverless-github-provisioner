# AWS Serverless Setup Guide

Complete guide to deploy the GitHub Repository Automation system on AWS.

---

## 🏗️ Architecture Overview

```
JIRA Ticket Created/Updated
        ↓
    JIRA Webhook (configured in JIRA)
        ↓
    API Gateway (POST /webhook)
        ↓
    Lambda: Webhook Handler
        ↓
    SQS Queue (Main Queue)
        ↓
    Lambda: Repository Creator (Event Source Mapping)
        ↓
    Success → Update JIRA → Done
    Failure → Retry (max 3 times)
        ↓
    Dead Letter Queue (DLQ)
        ↓
    Lambda: DLQ Handler
        ↓
    Update JIRA + Send SNS Alert
```

---

## 📋 Prerequisites

- **AWS Account** with appropriate permissions
- **AWS CLI** installed and configured
- **GitHub Classic Personal Access Token** (`repo` + `write:org` scopes)
- **JIRA API Token** and access
- **Python 3.9+** for local testing

---

## 🚀 Step-by-Step Implementation

---

## STEP 1: Create SQS Queues

### 1.1 Create Dead Letter Queue (DLQ)

**Using AWS Console:**
1. Go to **AWS Console** → **SQS**
2. Click **Create queue**
3. Configuration:
   - **Type:** Standard Queue
   - **Name:** `github-repo-creation-dlq`
   - **Visibility timeout:** 30 seconds
   - **Message retention:** 14 days (1209600 seconds)
   - **Receive message wait time:** 0 seconds
4. Click **Create queue**
5. **Copy the Queue ARN** (e.g., `arn:aws:sqs:us-east-1:123456789012:github-repo-creation-dlq`)

**Using AWS CLI:**
```bash
aws sqs create-queue \
  --queue-name github-repo-creation-dlq \
  --attributes '{
    "VisibilityTimeout": "30",
    "MessageRetentionPeriod": "1209600"
  }' \
  --region us-east-1
```

---

### 1.2 Create Main Queue with DLQ

**Using AWS Console:**
1. Click **Create queue**
2. Configuration:
   - **Type:** Standard Queue
   - **Name:** `github-repo-creation-queue`
   - **Visibility timeout:** 300 seconds (5 minutes)
   - **Message retention:** 4 days (345600 seconds)
   - **Dead-letter queue:** Enabled
     - **Choose existing queue:** `github-repo-creation-dlq`
     - **Maximum receives:** 3
3. Click **Create queue**
4. **Copy the Queue URL** (you'll need this for Lambda environment variables)

**Using AWS CLI:**
```bash
# Get DLQ ARN
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/github-repo-creation-dlq \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

# Create main queue
aws sqs create-queue \
  --queue-name github-repo-creation-queue \
  --attributes "{
    \"VisibilityTimeout\": \"300\",
    \"MessageRetentionPeriod\": \"345600\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --region us-east-1
```

---

## STEP 2: Store Secrets in AWS Secrets Manager

### 2.1 Store GitHub Credentials

**Using AWS Console:**
1. Go to **Secrets Manager** → **Store a new secret**
2. **Secret type:** Other type of secret
3. **Key-value pairs:**
   ```
   GITHUB_TOKEN = ghp_YourGitHubClassicTokenHere
   GITHUB_ORG = Repo-Creation-Automation
   ```
4. **Secret name:** `github-repo-automation/github`
5. Click **Store**
6. **Copy the Secret ARN**

**Using AWS CLI:**
```bash
aws secretsmanager create-secret \
  --name github-repo-automation/github \
  --secret-string '{
    "GITHUB_TOKEN": "ghp_YourGitHubClassicTokenHere",
    "GITHUB_ORG": "Repo-Creation-Automation"
  }' \
  --region us-east-1
```

---

### 2.2 Store JIRA Credentials

**Using AWS CLI:**
```bash
aws secretsmanager create-secret \
  --name github-repo-automation/jira \
  --secret-string '{
    "JIRA_URL": "https://your-domain.atlassian.net",
    "JIRA_EMAIL": "hiya.modi.here@gmail.com",
    "JIRA_API_TOKEN": "your-jira-api-token-here"
  }' \
  --region us-east-1
```

---

## STEP 3: Create IAM Role for Lambda

### 3.1 Create Trust Policy

Create file: `iam/trust-policy.json`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 3.2 Create IAM Policy

Create file: `iam/lambda-execution-policy.json`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:SendMessage"
      ],
      "Resource": [
        "arn:aws:sqs:*:*:github-repo-creation-queue",
        "arn:aws:sqs:*:*:github-repo-creation-dlq"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:github-repo-automation/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:github-repo-automation-alerts"
    }
  ]
}
```

### 3.3 Create IAM Role

**Using AWS CLI:**
```bash
# Create the role
aws iam create-role \
  --role-name GithubRepoAutomationLambdaRole \
  --assume-role-policy-document file://iam/trust-policy.json

# Attach the policy
aws iam put-role-policy \
  --role-name GithubRepoAutomationLambdaRole \
  --policy-name GithubRepoAutomationPolicy \
  --policy-document file://iam/lambda-execution-policy.json

# Get the Role ARN (you'll need this)
aws iam get-role \
  --role-name GithubRepoAutomationLambdaRole \
  --query 'Role.Arn' \
  --output text
```

---

## STEP 4: Create SNS Topic for Alerts

**Using AWS CLI:**
```bash
# Create SNS topic
aws sns create-topic \
  --name github-repo-automation-alerts \
  --region us-east-1

# Subscribe your email for alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT:github-repo-automation-alerts \
  --protocol email \
  --notification-endpoint hiya.modi.here@gmail.com

# Confirm the subscription via email
```

---

## STEP 5: Package Lambda Functions

### 5.1 Create Deployment Package

```bash
cd github-repo-auto/Github-Auto-Repo-Creation

# Create deployment directory
mkdir -p deployment

# Install dependencies
pip install -r requirements.txt -t deployment/

# Copy source code
cp -r src/* deployment/

# Create ZIP file for Lambda deployment
cd deployment
zip -r ../lambda-deployment.zip .
cd ..
```

---

## STEP 6: Deploy Lambda Functions

### 6.1 Deploy Webhook Handler Lambda

```bash
aws lambda create-function \
  --function-name github-repo-webhook-handler \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/GithubRepoAutomationLambdaRole \
  --handler webhook_handler.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{
    SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/github-repo-creation-queue,
    DEFAULT_GITHUB_ORG=Repo-Creation-Automation
  }" \
  --region us-east-1
```

### 6.2 Deploy Repository Creator Lambda

```bash
aws lambda create-function \
  --function-name github-repo-creator \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/GithubRepoAutomationLambdaRole \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{
    ENVIRONMENT=production
  }" \
  --region us-east-1
```

### 6.3 Deploy DLQ Handler Lambda

```bash
aws lambda create-function \
  --function-name github-repo-dlq-handler \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/GithubRepoAutomationLambdaRole \
  --handler dlq_handler.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment Variables="{
    SNS_TOPIC_ARN=arn:aws:sns:us-east-1:YOUR_ACCOUNT:github-repo-automation-alerts
  }" \
  --region us-east-1
```

---

## STEP 7: Configure Event Source Mappings

### 7.1 Connect Main Queue to Repository Creator

```bash
aws lambda create-event-source-mapping \
  --function-name github-repo-creator \
  --batch-size 1 \
  --event-source-arn arn:aws:sqs:us-east-1:YOUR_ACCOUNT:github-repo-creation-queue \
  --function-response-types ReportBatchItemFailures \
  --region us-east-1
```

### 7.2 Connect DLQ to DLQ Handler

```bash
aws lambda create-event-source-mapping \
  --function-name github-repo-dlq-handler \
  --batch-size 1 \
  --event-source-arn arn:aws:sqs:us-east-1:YOUR_ACCOUNT:github-repo-creation-dlq \
  --region us-east-1
```

---

## STEP 8: Create API Gateway

### 8.1 Create REST API

**Using AWS Console:**
1. Go to **API Gateway** → **Create API**
2. Choose **REST API** (not private)
3. **API name:** `github-repo-automation-webhook`
4. Click **Create API**

### 8.2 Create Resource and Method

1. Click **Actions** → **Create Resource**
   - **Resource Name:** webhook
   - **Resource Path:** /webhook
   - Click **Create Resource**

2. Select `/webhook` → **Actions** → **Create Method** → **POST**
   - **Integration type:** Lambda Function
   - **Lambda Function:** `github-repo-webhook-handler`
   - Click **Save** → **OK** to grant permissions

### 8.3 Deploy API

1. **Actions** → **Deploy API**
2. **Deployment stage:** `[New Stage]`
3. **Stage name:** `prod`
4. Click **Deploy**
5. **Copy the Invoke URL** (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod`)

---

## STEP 9: Configure JIRA Webhook

### 9.1 Create Webhook in JIRA

1. Go to **JIRA Settings** → **System** → **WebHooks**
2. Click **Create a WebHook**
3. Configuration:
   - **Name:** GitHub Repository Automation
   - **Status:** Enabled
   - **URL:** `https://YOUR_API_GATEWAY_URL/prod/webhook`
   - **Events:**
     - ✅ Issue: created
     - ✅ Issue: updated
   - **JQL Query** (optional, to filter):
     ```
     labels = "repo-automation"
     ```
4. Click **Create**

---

## STEP 10: Update JIRA Ticket Custom Fields

To enable structured data capture, create custom fields in JIRA:

### 10.1 Create Custom Fields

1. Go to **JIRA Settings** → **Issues** → **Custom fields**
2. Click **Create custom field**
3. Create the following fields:

| Field Name | Field Type | Description |
|-----------|-----------|-------------|
| Repository Name | Short Text | Name of the repository to create |
| GitHub Organization | Short Text | GitHub organization (default in settings) |
| Repository Visibility | Select List | Options: Private, Public |
| Repository Description | Paragraph | Description of the repository |
| Repository URL | URL | Auto-populated by automation |
| Repository Created Date | Date Picker | Auto-populated by automation |
| Creation Status | Select List | Options: Pending, In Progress, Completed, Failed |

### 10.2 Note Custom Field IDs

After creating fields, note their IDs:
1. Go to **Custom Fields** → Click on field name
2. Look at the URL: `customfield_10001` (the number is the ID)
3. Update `src/webhook_handler.py` with correct field IDs:

```python
# Line ~168 in webhook_handler.py
repo_name = fields.get('customfield_10001')  # Repository Name
github_org = fields.get('customfield_10002')  # GitHub Organization
repo_type = fields.get('customfield_10003', {}).get('value', 'Private')
description = fields.get('customfield_10004', '')
```

---

## STEP 11: Test the Integration

### 11.1 Manual Test via API Gateway

```bash
# Test webhook endpoint
curl -X POST https://YOUR_API_GATEWAY_URL/prod/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "jira:issue_created",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "issuetype": {"name": "Task"},
        "labels": ["repo-automation"],
        "status": {"name": "To Do"},
        "summary": "test-repository-name",
        "description": "Test repository description",
        "customfield_10001": "test-repository-name",
        "customfield_10002": "Repo-Creation-Automation",
        "customfield_10003": {"value": "Private"}
      }
    }
  }'
```

### 11.2 Check CloudWatch Logs

```bash
# View webhook handler logs
aws logs tail /aws/lambda/github-repo-webhook-handler --follow

# View repository creator logs
aws logs tail /aws/lambda/github-repo-creator --follow

# View DLQ handler logs
aws logs tail /aws/lambda/github-repo-dlq-handler --follow
```

### 11.3 Monitor SQS Queues

```bash
# Check main queue
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/github-repo-creation-queue \
  --attribute-names ApproximateNumberOfMessages

# Check DLQ
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/github-repo-creation-dlq \
  --attribute-names ApproximateNumberOfMessages
```

### 11.4 Create Test JIRA Ticket

1. Create a new JIRA ticket
2. Add label: `repo-automation`
3. Fill in custom fields:
   - **Repository Name:** `my-test-repo`
   - **GitHub Organization:** `Repo-Creation-Automation`
   - **Repository Visibility:** Private
   - **Repository Description:** Testing automation
4. Move ticket to "In Progress"
5. Watch for:
   - Repository created in GitHub
   - JIRA comment added
   - JIRA labels updated

---

## 🔧 Configuration Options

### Environment Variables

**Webhook Handler:**
- `SQS_QUEUE_URL`: Main SQS queue URL (required)
- `DEFAULT_GITHUB_ORG`: Default organization if not specified in ticket

**Repository Creator:**
- `ENVIRONMENT`: `production` or `development`
- Secrets loaded from AWS Secrets Manager

**DLQ Handler:**
- `SNS_TOPIC_ARN`: SNS topic for alerts (optional)

---

## 📊 Monitoring & Alerts

### CloudWatch Dashboards

Create a CloudWatch dashboard to monitor:
- Lambda invocation count
- Lambda error rate
- Lambda duration
- SQS queue depth
- DLQ message count

### CloudWatch Alarms

Set up alarms for:
1. **DLQ Messages > 0** → Send SNS alert
2. **Lambda Errors > 5 in 5 minutes** → Send SNS alert
3. **SQS Queue Depth > 10** → Warning
4. **Lambda Duration > 4 minutes** → Warning

### Example Alarm (DLQ Messages)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name github-repo-dlq-messages \
  --alarm-description "Alert when messages appear in DLQ" \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Average \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=github-repo-creation-dlq \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT:github-repo-automation-alerts
```

---

## 🛠️ Troubleshooting

### Issue: Webhook returns 403

**Cause:** API Gateway permission issue
**Solution:** Re-deploy API Gateway and ensure Lambda permissions are granted

### Issue: Repository not created

**Causes:**
1. GitHub token expired or invalid
2. Repository name validation failed
3. Organization access issue

**Solution:**
1. Check CloudWatch logs for error details
2. Verify GitHub token in Secrets Manager
3. Test GitHub API manually

### Issue: JIRA not updated

**Causes:**
1. JIRA credentials invalid
2. Ticket ID incorrect
3. Network/firewall issue

**Solution:**
1. Check CloudWatch logs
2. Verify JIRA credentials in Secrets Manager
3. Test JIRA API manually

### Issue: Messages stuck in queue

**Cause:** Lambda not processing messages
**Solution:**
1. Check Lambda concurrency limits
2. Verify event source mapping is enabled
3. Check IAM permissions

---

## 📈 Cost Estimation

### Monthly Cost (Estimated for ~100 repos/month)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda (Webhook) | 100 invocations, 128MB, 1s | $0.00 |
| Lambda (Creator) | 100 invocations, 512MB, 30s | $0.01 |
| Lambda (DLQ) | 5 invocations, 256MB, 5s | $0.00 |
| SQS | 100 messages | $0.00 |
| API Gateway | 100 requests | $0.00 |
| Secrets Manager | 2 secrets | $0.80 |
| CloudWatch Logs | 1GB | $0.50 |
| **Total** | | **~$1.31/month** |

*All services stay within AWS Free Tier for low-volume usage*

---

## 🎯 Next Steps

### MVP Complete! ✅

You now have:
- ✅ Webhook receiver (API Gateway + Lambda)
- ✅ Async processing (SQS)
- ✅ Repository creation (Lambda + GitHub)
- ✅ JIRA integration (comments + labels)
- ✅ Error handling (DLQ + alerts)
- ✅ Monitoring (CloudWatch)

### Future Enhancements

1. **JIRA Transitions** (from `docs/JIRA_TICKET_TRANSITIONS.md`)
   - Auto-transition on success
   - Categorized failure transitions

2. **JIRA Custom Fields**
   - Store repository URL
   - Store creation timestamp
   - Track creation status

3. **Advanced Features**
   - Repository templates
   - Team permissions
   - Branch protection
   - Initial files/README

4. **Infrastructure as Code**
   - Convert to CloudFormation/Terraform
   - Automate entire deployment

---

## 📚 Related Documentation

- [`JIRA_TICKET_TRANSITIONS.md`](./JIRA_TICKET_TRANSITIONS.md) - JIRA automation plan
- [`JIRA_TICKET_FIELDS.md`](./JIRA_TICKET_FIELDS.md) - Custom fields setup
- [`GITHUB_TESTING_GUIDE.md`](../GITHUB_TESTING_GUIDE.md) - GitHub testing
- [`LOCAL_TESTING_GUIDE.md`](../LOCAL_TESTING_GUIDE.md) - Local development

---

## 🆘 Support

**Questions or issues?**
- Review CloudWatch logs for detailed error messages
- Check this guide's troubleshooting section
- Contact Platform Team: hiya.modi.here@gmail.com

---

**Last Updated:** 2026-03-30
**Version:** 1.0

