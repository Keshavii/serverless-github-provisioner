# GitHub Repository Automation - System Architecture (Secondary)

## 📋 Document Information

- **Architecture Type:** Event-Driven Serverless with API Gateway
- **Version:** 1.0 (Secondary - Alternative Approach)
- **Last Updated:** March 27, 2026
- **Status:** Alternative Architecture

---

## 🎯 Overview

This document describes the **secondary alternative architecture** for the GitHub Repository Automation system using **AWS API Gateway** for JIRA webhook integration.

### Why This Architecture?

**✅ Enterprise-Ready:** Built-in request validation, throttling, and monitoring  
**✅ Custom Domain:** Support for custom domain names (api.hiyamodi.com)  
**✅ Advanced Auth:** Multiple authentication options (API keys, Cognito, etc.)  
**✅ Request Validation:** Schema validation before Lambda execution  
**✅ Rate Limiting:** Built-in throttling to protect backend  

### Primary Architecture

> **Note:** For the simpler, recommended architecture using **Lambda Function URL**, see [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 🏗️ High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         JIRA CLOUD                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Ticket Status Changed to "In Progress"                        │ │
│  │  Webhook Triggered                                             │ │
│  │  Custom Fields: repo_name, code_type, visibility, etc.        │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                   (HTTPS POST to API Gateway)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS API GATEWAY (REST API)                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Endpoint: POST /jira-webhook                                  │ │
│  │  Domain: https://api.hiyamodi.com/v1/jira-webhook               │ │
│  │  (or default AWS endpoint)                                     │ │
│  │                                                                 │ │
│  │  Features:                                                     │ │
│  │  • Request validation (JSON schema)                            │ │
│  │  • Authentication (API key or IAM)                             │ │
│  │  • Rate limiting (1000 req/sec)                                │ │
│  │  • Request/response transformation                             │ │
│  │  • Access logging                                              │ │
│  │  • CloudWatch metrics                                          │ │
│  │                                                                 │ │
│  │  Integration: AWS Service (SQS)                                │ │
│  │  • Direct SQS integration (no Lambda needed)                   │ │
│  │  • Or Lambda integration for validation                        │ │
│  │                                                                 │ │
│  │  Duration: ~50ms                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                   (Sends message to SQS)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS SQS (Standard Queue)                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Queue: repo-creation-queue                                    │ │
│  │                                                                 │ │
│  │  Message Attributes:                                           │ │
│  │  • jira_ticket_id                                              │ │
│  │  • repo_name                                                   │ │
│  │  • github_org                                                  │ │
│  │  • code_type                                                   │ │
│  │  • visibility                                                  │ │
│  │  • description                                                 │ │
│  │  • branch_protection_enabled                                   │ │
│  │  • required_reviewers                                          │ │
│  │  • topics (optional)                                           │ │
│  │  • license_template (optional)                                 │ │
│  │                                                                 │ │
│  │  Configuration:                                                │ │
│  │  • Retention: 14 days                                          │ │
│  │  • Visibility Timeout: 5 minutes                               │ │
│  │  • Max Receives: 3 (then → DLQ)                                │ │
│  │  • Encryption: At rest (AWS managed keys)                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                    (Lambda polls SQS)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              AWS LAMBDA (Repository Creator)                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Function: github-repo-creator                                 │ │
│  │  Runtime: Python 3.11                                          │ │
│  │  Memory: 512 MB                                                │ │
│  │  Timeout: 5 minutes                                            │ │
│  │  Concurrency: 10 (reserved)                                    │ │
│  │  Batch Size: 1 message at a time                               │ │
│  │                                                                 │ │
│  │  Steps:                                                        │ │
│  │  1. Parse SQS message                                          │ │
│  │  2. Validate required fields                                   │ │
│  │  3. Check if repository already exists                         │ │
│  │  4. Create GitHub repository                                   │ │
│  │  5. Configure repository settings                              │ │
│  │  6. Set up branch protection                                   │ │
│  │  7. Apply templates (README, .gitignore)                       │ │
│  │  8. Add repository topics/tags                                 │ │
│  │  9. Update JIRA ticket with repo URL                           │ │
│  │  10. Delete message from SQS (success)                         │ │
│  │                                                                 │ │
│  │  On Error:                                                     │ │
│  │  • Log error details (CloudWatch)                              │ │
│  │  • Update JIRA with error message                              │ │
│  │  • Raise exception (SQS retries)                               │ │
│  │  • After 3 retries → DLQ                                       │ │
│  │                                                                 │ │
│  │  Duration: 10-30 seconds                                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         ↓ (Success)                    ↓ (Failure after 3 retries)
         ↓                              ↓
┌──────────────────────┐    ┌──────────────────────────────────────┐
│   GITHUB REPO        │    │   AWS SQS (Dead Letter Queue)        │
│   ✅ Created         │    │  ┌────────────────────────────────┐  │
│   ✅ Configured      │    │  │  Queue: repo-creation-dlq      │  │
│   ✅ README added    │    │  │                                 │  │
│   ✅ Topics added    │    │  │  Failed Messages:              │  │
└──────────────────────┘    │  │  • Stored for investigation    │  │
         ↓                  │  │  • Retention: 14 days          │  │
         ↓                  │  │  • CloudWatch alarm triggered  │  │
┌──────────────────────┐    │  │  • Manual retry possible       │  │
│   JIRA TICKET        │    │  │  • SNS notification sent       │  │
│   ✅ Updated         │    │  └────────────────────────────────┘  │
│   ✅ Repo URL added  │    └──────────────────────────────────────┘
│   ✅ Comment added   │                     ↓
│   ✅ Label added     │         ┌──────────────────────────┐
└──────────────────────┘         │  CloudWatch Alarm        │
                                 │  • Monitors DLQ depth    │
                                 │  • SNS notification      │
                                 │  • Email/Slack alert     │
                                 └──────────────────────────┘
```

---

## 🔄 End-to-End Flow

### Step-by-Step Process

**Step 1: JIRA Ticket Status Change (0ms)**
- User updates JIRA ticket status to "In Progress"
- JIRA webhook fires with ticket data
- Webhook payload includes all custom fields

**Step 2: API Gateway Receives Request (10-30ms)**
- API Gateway receives HTTPS POST from JIRA
- Validates API key or IAM signature (if enabled)
- Validates request against JSON schema
- Logs request to CloudWatch
- Applies rate limiting rules

**Step 3: Request Transformation (30-50ms)**
- API Gateway transforms JIRA payload
- Extracts custom field values
- Maps to SQS message format
- Or forwards to Lambda for validation

**Step 4: Send to SQS (50-100ms)**
- API Gateway directly integrates with SQS
- Or Lambda validates and sends to SQS
- Message queued for processing
- Returns HTTP 200 to JIRA

**Step 5-12: Same as Primary Architecture**
- SQS queues message
- Lambda polls and processes
- GitHub repository created
- JIRA ticket updated
- Total: 10-30 seconds

---

## 🧩 Component Details

### Component 1: API Gateway (REST API)

**Purpose:** Receive JIRA webhooks with enterprise features

**Configuration:**
- **API Type:** REST API (not HTTP API for this use case)
- **Endpoint Type:** Regional
- **Custom Domain:** Optional (e.g., api.hiyamodi.com)
- **Stage:** v1 (production)

**Endpoint:**
- **Method:** POST
- **Path:** /jira-webhook
- **Full URL:** https://{api-id}.execute-api.{region}.amazonaws.com/v1/jira-webhook
- **Custom URL:** https://api.hiyamodi.com/v1/jira-webhook (if configured)

**Request Validation:**
- JSON schema validation
- Required fields check
- Field format validation
- Content-Type validation (application/json)

**Authentication Options:**

**Option 1: API Key**
- JIRA sends API key in header: `x-api-key: {key}`
- API Gateway validates before processing
- Keys managed in API Gateway console
- Can create multiple keys for different environments

**Option 2: IAM Authentication**
- JIRA signs request with AWS SIG v4
- API Gateway validates signature
- Most secure option
- Requires AWS credentials in JIRA

**Option 3: None (Public Endpoint)**
- No authentication
- Rely on obscure URL
- Not recommended for production

**Rate Limiting:**
- Throttle: 1,000 requests/second (configurable)
- Burst: 2,000 requests
- Per-client quotas available
- Protects backend from abuse

**Request/Response Transformation:**
- Transform JIRA webhook payload to SQS format
- Map custom field IDs to readable names
- Add metadata (timestamp, request ID)
- Return standardized response

**Integration Type:**

**Option A: AWS Service Integration (Direct to SQS)**
- API Gateway → SQS directly
- No Lambda needed for webhook reception
- Lowest latency and cost
- Uses VTL (Velocity Template Language) for transformation

**Option B: Lambda Proxy Integration**
- API Gateway → Lambda → SQS
- Lambda does validation and transformation
- More flexible
- Higher latency and cost

**Logging:**
- Access logs to CloudWatch
- Execution logs for debugging
- Full request/response logging
- Data masking for sensitive fields

---

### Component 2: Integration Architecture

**Two Integration Patterns:**

**Pattern 1: Direct SQS Integration (Recommended)**
```
API Gateway → SQS → Lambda (Repo Creator)
```
- Simpler architecture
- Lower latency
- Lower cost (no webhook Lambda)
- Less code to maintain

**Pattern 2: Lambda Integration**
```
API Gateway → Lambda (Validator) → SQS → Lambda (Repo Creator)
```
- More validation logic
- Custom transformation
- Better error handling
- More flexibility

**Comparison:**

| Aspect | Direct SQS | Lambda Integration |
|--------|-----------|-------------------|
| Latency | ✅ Lower (~50ms) | ❌ Higher (~200ms) |
| Cost | ✅ Cheaper | ❌ More expensive |
| Flexibility | ❌ Limited (VTL) | ✅ Full Python control |
| Complexity | ✅ Simpler | ❌ More components |
| Maintenance | ✅ Less code | ❌ More code |

---

## 📊 API Gateway-Specific Features

### Request Validation

**JSON Schema:**
- Define expected request structure
- Automatic validation before Lambda
- Returns 400 Bad Request if invalid
- Reduces Lambda invocations (cost savings)

**Validation Rules:**
- Required fields
- Field types (string, number, boolean)
- String patterns (regex)
- Min/max values
- Enum values

### Custom Domain Names

**Benefits:**
- Professional URL (api.hiyamodi.com)
- SSL/TLS certificates from ACM
- Consistent branding
- Version management (/v1, /v2)

**Setup:**
- Register domain in Route 53
- Request ACM certificate
- Create custom domain mapping
- Update DNS records

### Usage Plans & API Keys

**Usage Plans:**
- Define throttling limits per client
- Set quota (e.g., 1000 requests/day)
- Associate with API keys
- Monitor usage per key

**API Keys:**
- Create separate keys for environments
- Rotate keys regularly
- Disable/delete compromised keys
- Track usage per key

### Monitoring & Metrics

**Built-in Metrics:**
- Request count
- Latency (integration, overall)
- 4XX errors (client errors)
- 5XX errors (server errors)
- Cache hit/miss (if caching enabled)

**CloudWatch Integration:**
- Automatic metric collection
- Custom dashboards
- Alarms on error rates
- Detailed execution logs

---

## 💰 Cost Comparison

### Monthly Cost (100 repos/month)

**API Gateway Architecture:**

| Service | Cost | Notes |
|---------|------|-------|
| API Gateway | $3.50 | 100 requests × $3.50/million = $0.00035 |
| Lambda (optional validator) | $0.00 | Within free tier |
| Lambda (repo creator) | $0.02 | Same as primary |
| SQS | $0.00 | Within free tier |
| CloudWatch Logs | $0.50 | Same as primary |
| Secrets Manager | $0.80 | Same as primary |
| **Total** | **~$1.32** | Same as primary for low volume |

**Note:** API Gateway cost is negligible at low volumes but increases with scale.

**Scaling to 10,000 repos/month:**
- API Gateway: $0.035
- Lambda: $2.00
- Other: $1.30
- **Total: ~$3.37**

**vs Lambda Function URL (10,000 repos):**
- No API Gateway fees
- **Total: ~$3.00**

**Cost Difference:** $0.37/month (12% more expensive)

---

## ⚡ Performance Comparison

### Latency Breakdown

| Component | Lambda Function URL | API Gateway |
|-----------|-------------------|-------------|
| Webhook Reception | 100-200ms | 50-100ms (if direct SQS) |
| | | 200-300ms (if Lambda) |
| Request Validation | In Lambda | In API Gateway |
| Message to SQS | 50ms | 50ms |
| Lambda Processing | 10-30s | 10-30s |
| **Total** | **15-35 seconds** | **15-35 seconds** |

**Conclusion:** Similar total latency, API Gateway slightly faster webhook reception.

---

## 🔐 Security Comparison

| Security Feature | Lambda Function URL | API Gateway |
|-----------------|-------------------|-------------|
| HTTPS | ✅ Yes | ✅ Yes |
| API Keys | ❌ No | ✅ Yes |
| IAM Auth | ✅ Yes | ✅ Yes |
| WAF Integration | ❌ No | ✅ Yes |
| Request Validation | ❌ Manual in Lambda | ✅ Built-in |
| Rate Limiting | ❌ Manual | ✅ Built-in |
| Custom Domain | ❌ No | ✅ Yes |
| DDoS Protection | ✅ AWS Shield Standard | ✅ AWS Shield Standard |

**Conclusion:** API Gateway provides more enterprise security features.

---

## 📋 When to Use API Gateway Architecture

### Use API Gateway When:

✅ **Enterprise Requirements:**
- Need custom domain names
- Need API key authentication
- Need built-in rate limiting
- Need request schema validation

✅ **Advanced Features:**
- Need request/response transformation
- Need caching (for repeated requests)
- Need usage plans and quotas
- Need detailed API analytics

✅ **Security:**
- Need WAF integration
- Need multiple authentication methods
- Need IP whitelisting
- Need fine-grained access control

✅ **Compliance:**
- Need detailed access logs
- Need request/response logging
- Need audit trails
- Need API versioning

### Use Lambda Function URL When:

✅ **Simplicity:**
- Simple webhook endpoint
- Internal systems only
- No custom domain needed
- Minimal authentication requirements

✅ **Cost:**
- Budget-sensitive projects
- Low to medium volume
- Want to minimize services

✅ **Speed:**
- Quick prototyping
- Proof of concept
- Simple use cases

---

## ✅ Summary

### API Gateway Architecture Benefits

**Pros:**
- ✅ Enterprise-grade features
- ✅ Built-in request validation
- ✅ Custom domain support
- ✅ Advanced authentication
- ✅ Rate limiting and throttling
- ✅ Detailed monitoring and logging
- ✅ Professional API management

**Cons:**
- ❌ More complex setup
- ❌ Additional cost (minimal at low volume)
- ❌ Extra service to manage
- ❌ Steeper learning curve

### Comparison Summary

| Aspect | Lambda Function URL | API Gateway |
|--------|-------------------|-------------|
| **Setup Complexity** | ⭐⭐ Simple | ⭐⭐⭐⭐ Complex |
| **Cost (100 repos)** | $1.32 | $1.32 |
| **Cost (10K repos)** | $3.00 | $3.37 |
| **Features** | ⭐⭐ Basic | ⭐⭐⭐⭐⭐ Advanced |
| **Security** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Monitoring** | ⭐⭐⭐ CloudWatch | ⭐⭐⭐⭐⭐ API Gateway + CW |
| **Performance** | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Fast |
| **Maintenance** | ⭐⭐⭐⭐⭐ Low | ⭐⭐⭐ Medium |

### Recommendation

**For Most Teams:** Start with **Lambda Function URL** (Primary Architecture)
- Simpler to implement and test
- Lower learning curve
- Sufficient for internal automation
- Easy to migrate to API Gateway later if needed

**For Enterprise Teams:** Use **API Gateway** (Secondary Architecture)
- Better security and compliance
- Professional API management
- Advanced monitoring and analytics
- Worth the extra complexity

---

**End of Secondary Architecture Document**

> For the simpler recommended architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md)
