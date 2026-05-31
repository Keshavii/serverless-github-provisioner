# GitHub Auto Repo Creation - Requirements Document

## 📋 Document Information

- **Project Name:** GitHub Auto Repo Creation System
- **Version:** 1.0
- **Last Updated:** March 26, 2024
- **Owner:** Engineering Team
- **Status:** Requirements Gathering

---

## 🎯 Executive Summary

### Purpose
Automate the creation of GitHub repositories triggered by JIRA ticket status changes, eliminating manual repository setup and ensuring consistency across all repositories.

### Business Value
- ⏱️ **Time Savings:** Reduce repository setup from 30+ minutes to < 1 minute
- ✅ **Consistency:** Ensure all repositories follow organizational standards
- 🔒 **Compliance:** Automatic enforcement of security policies and naming conventions
- 📊 **Traceability:** Complete audit trail from JIRA ticket to repository creation
- 🤝 **Integration:** Seamless connection between project management (JIRA) and code management (GitHub)

### Scope
**In Scope:**
- Automated repository creation triggered by JIRA ticket status change
- Repository configuration (branch protection, settings, etc.)
- Template application (README, .gitignore, LICENSE, CI/CD)
- JIRA ticket updates with repository information
- Error handling and retry mechanism
- Audit logging

**Out of Scope (Future Phases):**
- Repository deletion/archival
- Multi-cloud repository support (GitLab, Bitbucket)
- Advanced approval workflows
- Repository migration tools

---

## 🏗️ System Architecture Overview

### High-Level Flow

```
JIRA Ticket Created
    ↓
RELB Sets Status to "In Progress"
    ↓
JIRA Webhook Triggers
    ↓
API Gateway Receives Event
    ↓
Message Sent to SQS Queue
    ↓
Lambda Function Triggered
    ↓
Repository Created in GitHub
    ↓
Repository Configured
    ↓
Templates Applied
    ↓
JIRA Ticket Updated with Repo URL
    ↓
Success Notification Sent
```

### Technology Stack

**Cloud Platform:** AWS  
**Programming Language:** Python 3.11  
**Key Services:**
- AWS Lambda (Compute)
- AWS SQS (Message Queue)
- AWS API Gateway (HTTP Endpoint)
- AWS CloudWatch (Logging & Monitoring)
- AWS Secrets Manager (Credentials)

**External Integrations:**
- GitHub (Repository Management)
- JIRA Cloud (Project Management)
- Slack/Teams (Notifications - optional)

---

## 📝 Functional Requirements

### FR-1: JIRA Webhook Integration

**Requirement ID:** FR-1  
**Priority:** HIGH  
**Description:** System must receive and process JIRA webhook events when ticket status changes to "In Progress"

**Acceptance Criteria:**
- ✅ Webhook endpoint accepts JIRA POST requests
- ✅ Validates JIRA webhook signature for security
- ✅ Filters events to only process "In Progress" status changes
- ✅ Extracts required fields from JIRA ticket
- ✅ Handles malformed or invalid payloads gracefully

**Required JIRA Custom Fields:**
| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| Repository Name | Text | Yes | Name of repository to create | `customer-service-api` |
| GitHub Organization | Text | Yes | Target GitHub organization | `hiyamodi` |
| Code Type | Dropdown | Yes | Technology stack | `java`, `nodejs`, `python` |
| Visibility | Dropdown | Yes | Repository visibility | `internal`, `private`, `public` |
| Description | Text Area | Yes | Repository description | "Customer service API..." |
| Auto Init | Checkbox | No | Initialize with README | Default: Yes |
| License | Dropdown | No | License type | `MIT`, `Apache-2.0` |
| Topics | Text (comma-separated) | No | Repository tags | `java,api,microservice` |

---

### FR-2: Message Queue Processing

**Requirement ID:** FR-2  
**Priority:** HIGH  
**Description:** System must queue repository creation requests for reliable processing

**Acceptance Criteria:**
- ✅ Messages sent to SQS queue with all required attributes
- ✅ Message retention: 14 days
- ✅ Visibility timeout: 7 minutes (enough for repo creation)
- ✅ Dead Letter Queue (DLQ) configured for failed messages
- ✅ Maximum receive count: 3 (retry 3 times before DLQ)

**Message Format:**
```json
{
  "jira_ticket_id": "DEVOPS-1234",
  "repo_name": "customer-service-api",
  "github_org": "hiyamodi",
  "description": "Customer service API for managing customer data",
  "visibility": "private",
  "code_type": "java",
  "auto_init": true,
  "has_issues": true,
  "has_wiki": false,
  "has_projects": false,
  "license_template": "mit",
  "gitignore_template": "Java",
  "topics": ["java", "spring-boot", "microservice"],
  "branch_protection_enabled": true,
  "required_reviewers": 2,
  "timestamp": "2024-03-26T10:30:00Z"
}
```

---

### FR-3: Input Validation

**Requirement ID:** FR-3  
**Priority:** HIGH  
**Description:** System must validate all input data before repository creation

**Validation Rules:**

**Repository Name:**
- ✅ Format: kebab-case (lowercase, numbers, hyphens only)
- ✅ Length: 3-100 characters
- ✅ Cannot start or end with hyphen
- ✅ Cannot contain consecutive hyphens (`--`)
- ✅ Cannot be reserved names: `admin`, `api`, `www`, `test`, `staging`, `production`, `dev`,`preprod`, `prod`
- ✅ Examples: ✅ `customer-api` ✅ `payment-service-v2` ❌ `CustomerAPI` ❌ `api--service`

**JIRA Ticket ID:**
- ✅ Format: `PROJECT-NUMBER` (e.g., `DEVOPS-1234`)
- ✅ Project code: 2-10 uppercase letters
- ✅ Number: 1-6 digits
- ✅ Examples: ✅ `DEVOPS-123` ✅ `PLATFORM-56789` ❌ `devops-123` ❌ `DEV123`

**GitHub Organization:**
- ✅ Must exist and be accessible
- ✅ User must have repository creation permissions
- ✅ Organization must not have reached repository limit

**Description:**
- ✅ Length: 10-500 characters
- ✅ Must be meaningful (not placeholder text like "test", "todo", "TBD")
- ✅ Cannot contain only URLs

**Code Type:**
- ✅ Allowed values: `java`, `nodejs`, `python`, `go`, `terraform`, `helm`, `react`, `angular`
- ✅ Must match available templates

**Visibility:**
- ✅ Allowed values: `private`, `public`, `internal`
- ✅ Note: `internal` requires GitHub Enterprise

**Topics (if provided):**
- ✅ Maximum 20 topics
- ✅ Each topic: lowercase, letters, numbers, hyphens only
- ✅ Maximum 50 characters per topic
- ✅ No duplicates
- ✅ Examples: ✅ `java`, `spring-boot`, `api` ❌ `Java`, `Spring Boot`, `API!!!`

---

### FR-4: GitHub Repository Creation

**Requirement ID:** FR-4  
**Priority:** HIGH  
**Description:** System must create GitHub repository with specified configuration

**Acceptance Criteria:**

**Basic Repository Creation:**
- ✅ Repository created in specified organization
- ✅ Name, description, visibility set correctly
- ✅ Check for duplicate repository names before creation
- ✅ Return repository URL, clone URL, SSH URL

**Repository Settings:**
- ✅ Issues enabled/disabled based on request
- ✅ Wiki enabled/disabled based on request
- ✅ Projects enabled/disabled based on request
- ✅ Default branch set to `main`
- ✅ License applied (if specified)
- ✅ .gitignore template applied (if specified)

---



### FR-6: Template Application

**Requirement ID:** FR-6
**Priority:** HIGH
**Description:** System must apply code templates based on repository type

**Acceptance Criteria:**

**README.md Generation:**
- ✅ Dynamic README generated based on code type
- ✅ Includes project name, description
- ✅ Includes getting started instructions
- ✅ Includes tech stack information
- ✅ Includes JIRA ticket reference
- ✅ Includes ownership information
- ✅ Includes project structure
- ✅ Includes build/run/test commands
- ✅ Professional formatting with proper sections

**README Structure:**
```markdown
# Repository Name

## Overview
[Description from request]

## Tech Stack
- Language: [Java/Node.js/Python/Go/etc.]
- Framework: [Auto-detected based on code_type]

## Getting Started
### Prerequisites
[Language-specific prerequisites]

### Installation
[Setup instructions]

### Running Locally
[Run commands]

### Running Tests
[Test commands]

## Project Structure
[Template directory structure]

## CI/CD
[Pipeline information]

## Related Links
- JIRA: [Ticket link]
- Documentation: [Confluence link]

## Contact
[Team information]
```

**.gitignore Generation:**
- ✅ Language-specific ignore patterns
- ✅ IDE-specific patterns (.idea/, .vscode/, .DS_Store)
- ✅ Build artifacts (target/, dist/, build/, node_modules/)
- ✅ Environment files (.env, .env.local)
- ✅ Log files (*.log)
- ✅ OS-specific files

**Supported Code Types and Templates:**

| Code Type | README Template | .gitignore | Additional Files |
|-----------|----------------|------------|------------------|
| `java` | Spring Boot setup | Java.gitignore | pom.xml skeleton, Dockerfile |
| `nodejs` | Node.js/Express setup | Node.gitignore | package.json skeleton, Dockerfile |
| `python` | FastAPI/Flask setup | Python.gitignore | requirements.txt, Dockerfile |
| `go` | Go module setup | Go.gitignore | go.mod skeleton, Dockerfile |
| `terraform` | Terraform module | Terraform.gitignore | main.tf, variables.tf, outputs.tf |
| `helm` | Helm chart | - | Chart.yaml, values.yaml |
| `react` | React app setup | Node.gitignore | package.json, Dockerfile |
| `angular` | Angular app setup | Node.gitignore | package.json, angular.json |

---

### FR-7: JIRA Ticket Update

**Requirement ID:** FR-7
**Priority:** HIGH
**Description:** System must update JIRA ticket upon successful repository creation

**Acceptance Criteria:**

**Success Case:**
- ✅ Add comment to JIRA ticket with repository details
- ✅ Update custom field with repository URL
- ✅ Add label: `repository-created`
- ✅ Add label: `automated`
- ✅ Optional: Transition ticket to next status (configurable)

**JIRA Comment Format:**
```
✅ Repository Created Successfully!

Repository: customer-service-api
URL: https://github.com/hiyamodi/customer-service-api
Visibility: private
Code Type: java
Branch Protection: Enabled

Created by: GitHub Auto Repo Creation System
Timestamp: 2024-03-26 10:35:42 UTC
Processing Time: 12.5 seconds

Repository Details:
- Clone URL: https://github.com/hiyamodi/customer-service-api.git
- SSH URL: git@github.com:hiyamodi/customer-service-api.git
- Default Branch: main
- Issues: Enabled
- Wiki: Disabled

Next Steps:
1. Clone the repository: git clone https://github.com/hiyamodi/customer-service-api.git
2. Review the README for setup instructions
3. Start development

Documentation: [Link to README]
```

**Failure Case:**
- ✅ Add comment with error details
- ✅ Add label: `repository-creation-failed`
- ✅ Keep ticket in current status
- ✅ Provide troubleshooting guidance

**JIRA Error Comment Format:**
```
❌ Repository Creation Failed

Repository: customer-service-api
Error: Repository name already exists in organization

Details:
- Request ID: req-abc123456
- Timestamp: 2024-03-26 10:30:15 UTC
- Retry Count: 3/3 (max retries exhausted)

Error Message:
Repository 'hiyamodi/customer-service-api' already exists.
Please choose a different name or contact support to recover the existing repository.

Troubleshooting:
1. Check if repository already exists: https://github.com/hiyamodi/customer-service-api
2. Choose a different repository name
3. Contact DevOps team if you need access to existing repository

For assistance, contact: hiya.modi.here@gmail.com
```

---

### FR-8: Error Handling and Retry Logic

**Requirement ID:** FR-8
**Priority:** HIGH
**Description:** System must handle errors gracefully with automatic retry mechanism

**Error Categories:**

**1. Transient Errors (Retry Automatically):**
- Network timeouts
- GitHub API rate limiting
- Temporary service unavailability
- Connection errors

**Retry Strategy:**
- Maximum retries: 3
- Backoff strategy: Exponential (2s, 4s, 8s)
- Total max time: ~15 seconds

**2. Permanent Errors (No Retry):**
- Invalid credentials
- Repository name already exists
- Insufficient permissions
- Invalid input data
- Organization not found

**Action:**
- Log error details
- Update JIRA ticket with error
- Send to Dead Letter Queue (DLQ)

**3. Partial Failures:**
- Repository created but configuration failed
- Repository created but template application failed

**Action:**
- Log successful steps
- Mark repository URL in JIRA
- Add warning comment about partial completion
- Don't delete repository (keep what was created)

**Acceptance Criteria:**
- ✅ Retry transient errors up to 3 times
- ✅ Don't retry permanent errors
- ✅ Log all errors with context (request ID, timestamp, error details)
- ✅ Update JIRA for all failures
- ✅ Send failed messages to DLQ after max retries
- ✅ Preserve partial progress
- ✅ No silent failures

---

### FR-9: Audit Logging

**Requirement ID:** FR-9
**Priority:** MEDIUM
**Description:** System must log all operations for audit and debugging

**Acceptance Criteria:**

**Log Events:**
- ✅ Request received (with all parameters)
- ✅ Validation started/completed/failed
- ✅ Repository creation started/completed/failed
- ✅ Branch protection applied/skipped/failed
- ✅ Templates applied (which ones)
- ✅ JIRA updated successfully/failed
- ✅ Request completed (with duration)

**Log Format:**
- Structured JSON logs (CloudWatch compatible)
- Include correlation ID for tracing
- Include timestamp (ISO 8601 format)
- Include severity level (DEBUG, INFO, WARNING, ERROR)

**Sample Log Entry:**
```json
{
  "timestamp": "2024-03-26T10:35:42.123Z",
  "level": "INFO",
  "event": "repository_created",
  "request_id": "req-abc123456",
  "jira_ticket": "DEVOPS-1234",
  "repo_name": "customer-service-api",
  "repo_url": "https://github.com/hiyamodi/customer-service-api",
  "duration_ms": 12543,
  "github_org": "hiyamodi",
  "visibility": "private",
  "code_type": "java"
}
```

**Log Retention:**
- CloudWatch Logs: 30 days (configurable)
- Critical errors: 90 days

---

## ⚡ Non-Functional Requirements

### NFR-1: Performance

**Requirement ID:** NFR-1
**Priority:** HIGH

**Performance Targets:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-end processing time | < 30 seconds | From JIRA webhook to repository creation complete |
| Lambda execution time | < 5 minutes | Maximum Lambda timeout |
| Lambda cold start | < 3 seconds | First invocation after deployment |
| API Gateway response | < 200ms | Webhook acknowledgment |
| GitHub API calls | < 10 seconds | Repository creation + configuration |
| JIRA API calls | < 5 seconds | Ticket updates |
| SQS message processing | < 1 second | Message delivery to Lambda |

**Throughput:**
- Handle 100 repository creation requests per hour
- Peak load: 10 concurrent requests
- Queue depth: Maximum 1000 messages

---

### NFR-2: Reliability

**Requirement ID:** NFR-2
**Priority:** HIGH

**Reliability Targets:**

| Metric | Target |
|--------|--------|
| Success rate | > 99% |
| Message delivery | 100% (with DLQ) |
| Retry success rate | > 90% |
| Data loss | 0% (guaranteed by SQS) |
| Idempotency | 100% (no duplicate repos) |

**Acceptance Criteria:**
- ✅ No message loss (SQS retention: 14 days)
- ✅ Automatic retry for transient failures
- ✅ Dead Letter Queue for persistent failures
- ✅ Idempotent operations (safe to retry)
- ✅ Graceful degradation (partial success handling)

---

### NFR-3: Security

**Requirement ID:** NFR-3
**Priority:** CRITICAL

**Security Requirements:**

**Authentication & Authorization:**
- ✅ JIRA webhook signature validation
- ✅ GitHub Personal Access Token stored in AWS Secrets Manager
- ✅ JIRA API credentials stored in AWS Secrets Manager
- ✅ Lambda execution role with least privilege permissions
- ✅ No hardcoded credentials in code

**Network Security:**
- ✅ API Gateway with HTTPS only (TLS 1.2+)
- ✅ Lambda in VPC (optional, if connecting to private resources)
- ✅ Security groups restrict access
- ✅ All external API calls over HTTPS

**Data Security:**
- ✅ No sensitive data in logs
- ✅ Mask credentials in error messages
- ✅ Encrypt data at rest (SQS, CloudWatch Logs)
- ✅ Encrypt data in transit (TLS)

**Repository Security:**
- ✅ Default visibility: `private`
- ✅ Branch protection enabled by default
- ✅ Require signed commits (configurable)
- ✅ Restrict force pushes and deletions

**Compliance:**
- ✅ Naming conventions enforced
- ✅ Repository naming audit trail
- ✅ Access control audit trail
- ✅ SOC 2 compliance ready (complete audit logs)

---

### NFR-4: Scalability

**Requirement ID:** NFR-4
**Priority:** MEDIUM

**Scalability Targets:**

**Lambda Scaling:**
- Concurrent executions: 10 (reserved)
- Burst capacity: 100 (unreserved)
- Auto-scaling: Enabled

**SQS Scaling:**
- Queue capacity: Unlimited (AWS managed)
- Message retention: 14 days
- In-flight messages: 120,000 (AWS limit)

**GitHub API Rate Limits:**
- Rate limit: 5,000 requests/hour (with token)
- Handle rate limit errors gracefully
- Implement exponential backoff

---

### NFR-5: Maintainability

**Requirement ID:** NFR-5
**Priority:** MEDIUM

**Code Quality:**
- ✅ Python 3.11+ (latest stable)
- ✅ Type hints for all functions
- ✅ Docstrings for all public methods
- ✅ Unit test coverage: > 80%
- ✅ Integration test coverage: > 60%
- ✅ Linting: Black, Flake8, mypy
- ✅ Code structure: Clean, modular, reusable

**Documentation:**
- ✅ Inline code comments for complex logic
- ✅ README with setup instructions
- ✅ API documentation (request/response formats)
- ✅ Deployment guide
- ✅ Troubleshooting guide
- ✅ Architecture diagrams

**Monitoring:**
- ✅ CloudWatch dashboards
- ✅ CloudWatch alarms for errors
- ✅ Metrics: success rate, latency, errors
- ✅ DLQ monitoring with alerts

---

### NFR-6: Usability

**Requirement ID:** NFR-6
**Priority:** LOW

**User Experience:**
- ✅ Clear error messages in JIRA comments
- ✅ Helpful troubleshooting guidance
- ✅ Links to documentation
- ✅ Professional formatting (emojis, sections)
- ✅ Estimated processing time communicated

**JIRA Integration:**
- ✅ Minimal custom fields required
- ✅ Intuitive field names
- ✅ Dropdown options for common values
- ✅ Clear field descriptions
- ✅ Validation errors shown immediately

---

## 🎯 Success Criteria

### Must-Have (MVP)
1. ✅ **JIRA Integration:** Webhook triggers on "In Progress" status
2. ✅ **Repository Creation:** Successfully creates GitHub repository
3. ✅ **Input Validation:** Enforces naming conventions and validates all fields
4. ✅ **JIRA Update:** Updates ticket with repository URL or error message
5. ✅ **Error Handling:** Retries transient errors, uses DLQ for permanent failures
6. ✅ **Audit Logging:** All operations logged to CloudWatch

### Should-Have (Phase 2)
1. ⭕ **Branch Protection:** Configures branch protection rules
2. ⭕ **Templates:** Applies README and .gitignore templates
3. ⭕ **Topics/Tags:** Adds repository topics for discoverability
4. ⭕ **Monitoring Dashboard:** CloudWatch dashboard for metrics
5. ⭕ **Alerts:** SNS notifications for DLQ messages

### Nice-to-Have (Future)
1. ⭕ **CI/CD Setup:** Automatically creates GitHub Actions workflows
2. ⭕ **Team Assignment:** Adds collaborators and teams
3. ⭕ **Slack Notifications:** Success/failure notifications
4. ⭕ **Approval Workflow:** Require approval for public repositories
5. ⭕ **Repository Templates:** Use GitHub template repositories

---

## 📊 Key Metrics & KPIs

### Operational Metrics
| Metric | Target | How to Measure |
|--------|--------|----------------|
| Repository creation success rate | > 99% | CloudWatch Metrics |
| Average processing time | < 30 seconds | CloudWatch Logs analysis |
| Failed messages in DLQ | < 1% | SQS DLQ message count |
| Lambda error rate | < 1% | CloudWatch Metrics |
| GitHub API rate limit errors | < 0.1% | CloudWatch Logs |

### Business Metrics
| Metric | Target | How to Measure |
|--------|--------|----------------|
| Repositories created per month | Track trend | CloudWatch custom metric |
| Time saved per repository | ~30 minutes | Manual vs automated |
| Developer satisfaction | > 4/5 | Survey |
| JIRA ticket resolution time | Reduced by 30% | JIRA reports |

---

## 🚀 Implementation Phases

### Phase 1: Local Development & Testing (Week 1-2)
**Goal:** Build core Lambda function, test locally without AWS

**Tasks:**
1. ✅ Set up project structure
2. ✅ Implement input validation (Pydantic schemas)
3. ✅ Implement GitHub client wrapper (PyGithub)
4. ✅ Implement JIRA client wrapper (jira library)
5. ✅ Create template engine for README generation
6. ✅ Implement main handler logic
7. ✅ Create local testing script (mock SQS messages)
8. ✅ Write unit tests (pytest)
9. ✅ Test with personal GitHub account

**Deliverables:**
- Working Lambda function code
- Unit tests with >80% coverage
- Local testing documentation
- Sample test data

**No AWS/JIRA needed:** Test with mocked data and personal GitHub account

---

### Phase 2: AWS Deployment (Week 3)
**Goal:** Deploy to AWS, integrate SQS

**Tasks:**
1. ✅ Set up AWS account and credentials
2. ✅ Store secrets in AWS Secrets Manager
3. ✅ Create SQS queue (standard + DLQ)
4. ✅ Package Lambda function with dependencies
5. ✅ Deploy Lambda function
6. ✅ Configure Lambda-SQS trigger
7. ✅ Set up CloudWatch logging
8. ✅ Test with manual SQS messages
9. ✅ Set up monitoring and alarms

**Deliverables:**
- Deployed Lambda function
- Configured SQS queues
- CloudWatch dashboards
- Deployment documentation

**AWS resources needed:** Lambda, SQS, Secrets Manager, CloudWatch

---

### Phase 3: JIRA Integration (Week 4)
**Goal:** Connect JIRA webhook to trigger workflow

**Tasks:**
1. ✅ Create JIRA custom fields
2. ✅ Set up API Gateway endpoint
3. ✅ Implement webhook signature validation
4. ✅ Configure JIRA webhook
5. ✅ Test end-to-end flow
6. ✅ Handle webhook failures
7. ✅ Test with real JIRA tickets
8. ✅ Train users on new workflow

**Deliverables:**
- API Gateway endpoint
- JIRA webhook configured
- User documentation
- Training materials

**JIRA setup needed:** Admin access to create custom fields and webhooks

---

## 🔧 Technical Constraints

### AWS Limits
- Lambda timeout: 15 minutes (max)
- Lambda package size: 50 MB (zipped), 250 MB (unzipped)
- SQS message size: 256 KB (max)
- SQS message retention: 14 days (max)
- API Gateway payload: 10 MB (max)

### GitHub Limits
- API rate limit: 5,000 requests/hour (authenticated)
- Repository name: 100 characters (max)
- Repository topics: 20 (max)
- Organization repositories: Varies by plan

### JIRA Limits
- Webhook timeout: 10 seconds
- Comment size: 32,767 characters (max)
- Custom fields: 200 per project (recommended limit)

---

## 📋 Dependencies

### External Services
| Service | Purpose | Required | Credentials Needed |
|---------|---------|----------|-------------------|
| GitHub | Repository creation | Yes | Personal Access Token (PAT) |
| JIRA Cloud | Ticket management | Yes | Email + API Token |
| AWS | Infrastructure | Yes | IAM credentials |
| Slack/Teams | Notifications | No | Webhook URL |

### Python Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| boto3 | 1.34+ | AWS SDK |
| PyGithub | 2.1+ | GitHub API |
| jira | 3.6+ | JIRA API |
| pydantic | 2.6+ | Data validation |
| structlog | 24.1+ | Logging |
| tenacity | 8.2+ | Retry logic |
| pytest | 8.0+ | Testing |

---

## 🎓 Prerequisites

### For Development
- Python 3.11+
- GitHub account with organization access
- JIRA Cloud account (admin access for webhook setup)
- AWS account (free tier sufficient for testing)
- Basic knowledge of AWS Lambda, SQS

### For Deployment
- AWS CLI configured
- GitHub Personal Access Token with `repo` scope
- JIRA API token
- Network access to GitHub and JIRA APIs

---

## 📞 Support & Contact

### Stakeholders
- **Product Owner:** [Name]
- **Engineering Lead:** [Name]
- **DevOps Team:** hiya.modi.here@gmail.com
- **JIRA Admin:** hiya.modi.here@gmail.com

### Resources
- Project Repository: [GitHub URL]
- Documentation: [Confluence URL]
- Issue Tracker: [JIRA Project]
- Monitoring Dashboard: [CloudWatch Dashboard URL]

---

## 📝 Appendix

### Glossary

**Kebab-case:** Naming convention using lowercase letters, numbers, and hyphens (e.g., `customer-service-api`)

**Personal Access Token (PAT):** GitHub authentication token for API access

**Dead Letter Queue (DLQ):** SQS queue for messages that failed processing after maximum retries

**Idempotent:** Operation that produces the same result when called multiple times

**Exponential Backoff:** Retry strategy that increases wait time exponentially between retries

---

## ✅ Document Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Engineering Lead | | | |
| DevOps Lead | | | |
| Security Review | | | |

---

**End of Requirements Document**

