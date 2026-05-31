# GitHub Repository Automation - Final Architecture

## 📋 Document Information

- **Architecture Type:** Event-Driven Serverless (Black Box Infrastructure)
- **Version:** 2.0 (Final)
- **Last Updated:** March 27, 2026
- **Status:** Final Approved Architecture




---

## 🔄 Complete Function Execution Flow

### Detailed Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     JIRA TICKET STATUS CHANGE                   │
│                   Status → "In Progress"                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (JIRA Webhook Triggered)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              🔲 INFRASTRUCTURE BLACK BOX                        │
│  • Receives webhook                                             │
│  • Queues message                                               │
│  • Triggers function execution                                  │
│  • Handles retries (3 attempts with exponential backoff)        │
│  • Moves to DLQ after 3 failures                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (Triggers Main Handler)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  FUNCTION 1: INPUT VALIDATION                   │
│                                                                 │
│  Validates:                                                     │
│  • repo_name (kebab-case, no spaces)                            │
│  • github_org (not empty)                                       │
│  • vp_name, director_name, em_name (ownership chain)            │
│  • documentation_link (valid URL format)                        │
│  • product_line, department (not empty)                         │
│  • repo_type (Internal or Private)                              │
│  • code_type (Java/Nodejs/Go/Python/terraform/helm)             │
│                                                                 │
│  Returns: validated_data object                                │
│  Raises: ValidationError (non-retryable)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         (Valid?)
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
                 ✅ YES              ❌ NO (ValidationError)
                    │                   │
                    ↓                   ↓
                    │         ┌─────────────────────────────────┐
                    │         │ FUNCTION 5: Update JIRA Failure │
                    │         │                                 │
                    │         │ Add comment to JIRA:            │
                    │         │ "❌ Validation Failed"          │
                    │         │                                 │
                    │         │ Include error details:          │
                    │         │ • Which field failed            │
                    │         │ • Expected format               │
                    │         │ • How to fix                    │
                    │         │                                 │
                    │         │ Add label: 'validation-failed'  │
                    │         │                                 │
                    │         │ RETURN/EXIT                     │
                    │         │ (No retry - permanent failure)  │
                    │         └─────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────┐
│            FUNCTION 2: REPOSITORY EXISTENCE CHECK               │
│                                                                 │
│  Operations:                                                    │
│  • Connect to GitHub API with PAT                               │
│  • Check if repo exists: GET /repos/{org}/{repo}                │
│  • Handle 404 (Not Found) → Repo doesn't exist                  │
│  • Handle 200 (OK) → Repo already exists                        │
│                                                                 │
│  Returns: (exists: boolean, repo_data: object or None)         │
│  Raises: GitHubAPIError (retryable - network/API issues)        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (Repo Exists?)
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              ❌ NOT EXISTS        ✅ ALREADY EXISTS
                    │                   │
                    ↓                   ↓
                    │         ┌─────────────────────────────────┐
                    │         │ IDEMPOTENT HANDLING             │
                    │         │                                 │
                    │         │ Get existing repository details:│
                    │         │ • Repository URL                │
                    │         │ • Clone URL (HTTPS)             │
                    │         │ • Clone URL (SSH)               │
                    │         │ • Repository ID                 │
                    │         │                                 │
                    │         │ SKIP to FUNCTION 4              │
                    │         │ (Update JIRA with existing URL) │
                    │         │                                 │
                    │         │ Note: This makes the process    │
                    │         │ idempotent - safe to retry      │
                    │         └─────────────────────────────────┘
                    ↓                   │
                    │                   │
                    │                   └──────────────┐
                    ↓                                  │
┌─────────────────────────────────────────────────────┼──────────┐
│            FUNCTION 3: GITHUB REPOSITORY CREATION   │          │
│                                                     │          │
│  Operations:                                        │          │
│  • Authenticate with GitHub (PAT from secrets)      │          │
│  • POST /orgs/{org}/repos with payload:             │          │
│    - name: {repo_name}                              │          │
│    - description: {description}                     │          │
│    - private: true (if repo_type = "Private")       │          │
│    - visibility: "internal" (if repo_type = "Internal") │      │
│    - auto_init: false                               │          │
│    - has_issues: false                              │          │
│    - has_wiki: false                                │          │
│    - has_projects: false                            │          │
│    - default_branch: "main"                         │          │
│                                                     │          │
│  Returns: repository_data (URL, clone_url, ssh_url, id) │     │
│  Raises: GitHubAPIError (retryable)                 │          │
└─────────────────────────────────────────────────────┼──────────┘
                              ↓                       │
                    (Creation Success?)               │
                              ↓                       │
                    ┌─────────┴─────────┐             │
                    │                   │             │
                 ✅ YES              ❌ NO            │
                    │                   │             │
                    ↓                   ↓             │
                    │         ┌─────────────────────────────────┐
                    │         │ GitHub API Error                │
                    │         │                                 │
                    │         │ Error Types:                    │
                    │         │ • 422: Validation failed        │
                    │         │ • 403: Permission denied        │
                    │         │ • 500: GitHub server error      │
                    │         │ • Network timeout               │
                    │         │                                 │
                    │         │ RAISE GitHubAPIError            │
                    │         │ (Retryable exception)           │
                    │         │                                 │
                    │         │ Infrastructure will:            │
                    │         │ • Retry attempt 1 (after 1s)    │
                    │         │ • Retry attempt 2 (after 2s)    │
                    │         │ • Retry attempt 3 (after 4s)    │
                    │         │ • If all fail → Move to DLQ     │
                    │         └─────────────────────────────────┘
                    ↓                   │
                    │                   ↓
                    │         (After 3 retries, still failing)
                    │                   │
                    │                   ↓
                    │         ┌─────────────────────────────────┐
                    │         │  DEAD LETTER QUEUE (DLQ)        │
                    │         │                                 │
                    │         │ Failed message stored with:     │
                    │         │ • Original event data           │
                    │         │ • Error details                 │
                    │         │ • Retry count (3)               │
                    │         │ • Timestamps                    │
                    │         │                                 │
                    │         │ Retention: 14 days              │
                    │         │                                 │
                    │         │ Triggers: DLQ Handler Function  │
                    │         └─────────────────────────────────┘
                    │                   │
                    │                   ↓
                    │         ┌─────────────────────────────────┐
                    │         │ FUNCTION 6: DLQ Handler         │
                    │         │                                 │
                    │         │ Parse DLQ message               │
                    │         │ Extract JIRA ticket ID          │
                    │         │                                 │
                    │         │ Call update_jira_failure():     │
                    │         │ "❌ Failed after 3 retries"     │
                    │         │                                 │
                    │         │ Include in comment:             │
                    │         │ • Error type and message        │
                    │         │ • All 3 retry timestamps        │
                    │         │ • Troubleshooting steps         │
                    │         │ • Contact: platform-team@       │
                    │         │                                 │
                    │         │ Send alert:                     │
                    │         │ • Email to platform team        │
                    │         │ • Slack notification (optional) │
                    │         │                                 │
                    │         │ Add labels:                     │
                    │         │ • 'repository-creation-failed'  │
                    │         │ • 'needs-manual-intervention'   │
                    │         │                                 │
                    │         │ RETURN/EXIT                     │
                    │         └─────────────────────────────────┘
                    ↓
                    │◄──────────────────────────────────────────┘
                    ↓ (Both paths converge here)
┌─────────────────────────────────────────────────────────────────┐
│           FUNCTION 4: JIRA TICKET UPDATE (SUCCESS)              │
│                                                                 │
│  Operations:                                                    │
│  • Authenticate with JIRA (credentials from secrets)            │
│                                                                 │
│  • Add comment to JIRA ticket:                                  │
│    ┌───────────────────────────────────────────────────────┐   │
│    │ ✅ Repository Created Successfully!                   │   │
│    │                                                        │   │
│    │ Repository Details:                                   │   │
│    │ • Name: {repo_name}                                   │   │
│    │ • Organization: {github_org}                          │   │
│    │ • Type: {repo_type}                                   │   │
│    │                                                        │   │
│    │ Repository URLs:                                      │   │
│    │ • Web: https://github.com/{org}/{repo}                │   │
│    │ • Clone (HTTPS): https://github.com/{org}/{repo}.git  │   │
│    │ • Clone (SSH): git@github.com:{org}/{repo}.git        │   │
│    │                                                        │   │
│    │ Processing Time: {duration} seconds                   │   │
│    │ Timestamp: {timestamp}                                │   │
│    │                                                        │   │
│    │ Next Steps:                                           │   │
│    │ 1. Clone the repository                               │   │
│    │ 2. Push your initial code                             │   │
│    │ 3. Verify and close this CR                           │   │
│    └───────────────────────────────────────────────────────┘   │
│                                                                 │
│  • Update custom field with repository URL (if configured)      │
│  • Add labels: 'repository-created', 'automated'                │
│                                                                 │
│  Returns: success_status                                       │
│  Raises: JiraAPIError (retryable)                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (JIRA Update Success?)
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
                 ✅ YES              ❌ NO (JiraAPIError)
                    │                   │
                    ↓                   ↓
        ┌──────────────────┐  ┌─────────────────────────────────┐
        │  ✅ SUCCESS!     │  │ JIRA API Error                  │
        │                  │  │ (Repo created but JIRA failed)  │
        │ Repository       │  │                                 │
        │ created on GitHub│  │ RAISE JiraAPIError              │
        │ and JIRA updated │  │ (Retryable exception)           │
        │                  │  │                                 │
        │ Message deleted  │  │ Infrastructure will:            │
        │ from queue       │  │ • Retry 3 times                 │
        │                  │  │ • If still fails → DLQ          │
        │ RETURN SUCCESS   │  │                                 │
        │                  │  │ DLQ Handler will update JIRA    │
        │ Duration:        │  │ with final error message        │
        │ 10-30 seconds    │  │                                 │
        └──────────────────┘  └─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│         FUNCTION 7: LOGGING & MONITORING (Continuous)           │
│                                                                 │
│  Runs throughout entire execution:                              │
│                                                                 │
│  • Log all function entries/exits                               │
│  • Log with structured format (JSON):                           │
│    - timestamp (ISO 8601)                                       │
│    - level (INFO, WARN, ERROR)                                  │
│    - correlation_id (for tracing)                               │
│    - jira_ticket_id                                             │
│    - repo_name                                                  │
│    - function_name                                              │
│    - duration_ms                                                │
│    - message                                                    │
│    - context (additional data)                                  │
│                                                                 │
│  • Emit custom metrics:                                         │
│    - repository_creation_success (counter)                      │
│    - repository_creation_failure (counter)                      │
│    - repository_already_exists (counter)                        │
│    - validation_failure (counter)                               │
│    - processing_duration_ms (histogram)                         │
│    - github_api_call_duration_ms (histogram)                    │
│    - jira_api_call_duration_ms (histogram)                      │
│                                                                 │
│  • Mask sensitive data in logs:                                 │
│    - GitHub tokens                                              │
│    - JIRA credentials                                           │
│    - Personal information                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Sequential Execution Summary

```
1. Input Validation
   ↓ (Valid)
2. Repository Existence Check
   ↓
   ├─ (Not Exists) → 3. Create Repository → 4. Update JIRA Success
   │
   └─ (Already Exists) → Get existing repo data → 4. Update JIRA Success
                        (Idempotent - safe to retry)

If validation fails → 5. Update JIRA Failure → EXIT
If GitHub API fails → Retry 3x → DLQ → 6. DLQ Handler → EXIT
If JIRA API fails → Retry 3x → DLQ → 6. DLQ Handler → EXIT

7. Logging & Monitoring (runs continuously throughout)
```

---

## � Main Handler Implementation Pattern

### Pseudo-code for Main Handler

```
def main_handler(event, context):
    """
    Main entry point triggered by infrastructure when message arrives from queue.

    Args:
        event: Event data from infrastructure (contains JIRA webhook payload)
        context: Execution context (timeout, request_id, etc.)

    Returns:
        Success response or raises exception for retry
    """

    # Initialize logging with correlation ID
    correlation_id = generate_correlation_id()
    log_and_monitor("handler_started", correlation_id=correlation_id)

    try:
        # STEP 1: Input Validation (Non-retryable)
        log_and_monitor("validating_input")
        try:
            validated_data = validate_input(event)
        except ValidationError as e:
            # Validation errors are permanent - update JIRA and exit
            log_and_monitor("validation_failed", error=str(e), level="ERROR")
            update_jira_failure(
                ticket_id=event.get('jira_ticket_id'),
                error_message=f"Validation Failed: {str(e)}"
            )
            return {"status": "failed", "reason": "validation_error"}

        # STEP 2: Repository Existence Check (Retryable)
        log_and_monitor("checking_repository_existence")
        exists, existing_repo_data = check_repository_exists(
            org=validated_data['github_org'],
            repo_name=validated_data['repo_name']
        )

        if exists:
            # IDEMPOTENT: Repo already exists - treat as success
            log_and_monitor("repository_already_exists",
                          repo_url=existing_repo_data['html_url'])
            repo_data = existing_repo_data
        else:
            # STEP 3: Create Repository (Retryable)
            log_and_monitor("creating_repository")
            repo_data = create_github_repository(validated_data)
            log_and_monitor("repository_created",
                          repo_url=repo_data['html_url'])

        # STEP 4: Update JIRA with Success (Retryable)
        log_and_monitor("updating_jira_success")
        update_jira_success(
            ticket_id=validated_data['jira_ticket_id'],
            repo_data=repo_data
        )

        log_and_monitor("handler_completed", status="success")
        return {
            "status": "success",
            "repo_url": repo_data['html_url'],
            "repo_name": repo_data['name']
        }

    except (GitHubAPIError, JiraAPIError) as e:
        # Retryable errors - raise exception for infrastructure to retry
        log_and_monitor("retryable_error_occurred",
                       error_type=type(e).__name__,
                       error=str(e),
                       level="ERROR")
        raise  # Infrastructure will retry up to 3 times

    except Exception as e:
        # Unexpected errors - log and raise for retry
        log_and_monitor("unexpected_error",
                       error_type=type(e).__name__,
                       error=str(e),
                       level="ERROR")
        raise


def dlq_handler(dlq_event, context):
    """
    Handler for Dead Letter Queue messages (failed after all retries).

    Args:
        dlq_event: Failed event data from DLQ
        context: Execution context

    Returns:
        Notification status
    """

    log_and_monitor("dlq_handler_started")

    # Extract original message and error details
    original_event = parse_dlq_message(dlq_event)
    jira_ticket_id = original_event.get('jira_ticket_id')
    error_history = dlq_event.get('error_history', [])

    # Update JIRA with final failure message
    error_summary = "Repository creation failed after 3 retry attempts."
    error_details = format_error_details(error_history)

    try:
        update_jira_failure(
            ticket_id=jira_ticket_id,
            error_message=f"{error_summary}\n\n{error_details}"
        )
    except Exception as e:
        # Best effort - log if JIRA update fails
        log_and_monitor("dlq_jira_update_failed",
                       error=str(e),
                       level="WARN")

    # Send alert to team
    send_alert_to_team(
        subject=f"Repository Creation Failed: {jira_ticket_id}",
        message=error_summary,
        details=error_details
    )

    log_and_monitor("dlq_handler_completed")
    return {"status": "notified"}
```

### Error Classification

**Non-Retryable Errors (Permanent Failures):**
- ❌ Validation errors (invalid repo name, missing fields, etc.)
- ❌ Authentication errors (invalid GitHub token, JIRA credentials)
- ❌ Permission errors (no access to org, forbidden)

**Action:** Update JIRA with error, return immediately (no retry)

**Retryable Errors (Transient Failures):**
- ✅ GitHub API rate limit (429)
- ✅ GitHub server errors (500, 502, 503)
- ✅ JIRA API server errors (500, 503)
- ✅ Network timeouts
- ✅ Temporary connection errors

**Action:** Raise exception, let infrastructure retry up to 3 times

**DLQ Handling (Exhausted Retries):**
- After 3 failed retry attempts
- Message moved to Dead Letter Queue
- DLQ handler triggered
- Update JIRA with final error
- Alert platform team

---

## �🔧 Technical Requirements

### Dependencies

**Core Libraries:**
- GitHub API Client (e.g., PyGithub, Octokit)
- JIRA API Client (e.g., jira-python, atlassian-python-api)
- Data Validation Library (e.g., Pydantic, marshmallow)
- HTTP Client (e.g., requests, httpx)
- Logging Library (e.g., structlog, python-json-logger)

**Infrastructure SDKs (if using cloud):**
- AWS SDK (boto3) - for Secrets Manager, CloudWatch
- Azure SDK - for Key Vault, Application Insights
- GCP SDK - for Secret Manager, Cloud Logging

### Environment Configuration

**Required Environment Variables:**
- `GITHUB_TOKEN_SECRET_NAME` - Secret name for GitHub PAT
- `JIRA_CREDENTIALS_SECRET_NAME` - Secret name for JIRA credentials
- `JIRA_BASE_URL` - JIRA instance URL
- `GITHUB_ORGANIZATION` - Default GitHub organization
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARN, ERROR)
- `ENABLE_BRANCH_PROTECTION` - Enable/disable branch protection
- `REQUIRED_REVIEWERS_COUNT` - Number of required reviewers

**Optional Environment Variables:**
- `CUSTOM_DOMAIN` - Custom domain for repository URLs
- `SLACK_WEBHOOK_URL` - Slack notification webhook
- `EMAIL_NOTIFICATION_ADDRESS` - Email for notifications
- `TEMPLATE_STORAGE_LOCATION` - Custom template storage path

### Secrets Management

**GitHub Personal Access Token (PAT):**
- Required scopes: `repo`, `admin:org`
- Storage: Cloud secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotation: Every 90 days (automated)

**JIRA Credentials:**
- Email + API Token
- Storage: Cloud secrets manager
- Rotation: Every 90 days (automated)

---

## 🎯 Infrastructure Black Box Requirements

### What the Infrastructure Layer Must Provide

**1. Event Reception:**
- Accept HTTPS POST requests from JIRA webhook
- Return HTTP 200 response within 10 seconds
- Handle webhook signature validation (optional)

**2. Message Queuing:**
- Queue messages reliably (at-least-once delivery)
- Retain messages for 14 days
- Support message visibility timeout (5 minutes)
- Dead Letter Queue (DLQ) for failed messages

**3. Function Execution:**
- Trigger core functions when message available
- Provide runtime environment (Python 3.11+)
- Set timeout (5 minutes minimum)
- Support concurrency (10+ concurrent executions)

**4. Retry Mechanism:**
- Automatic retry on failure (3 attempts)
- Exponential backoff between retries
- Move to DLQ after max retries

**5. Observability:**
- Collect logs from all executions
- Emit execution metrics (duration, errors, count)
- Support structured logging (JSON)
- Provide request tracing (correlation IDs)

**6. Security:**
- Encrypt data at rest and in transit
- Manage secrets securely
- Support IAM/RBAC for access control
- Network isolation (optional)

### Implementation Options

**Option 1: AWS**
- Lambda Function URL → SQS → Lambda
- Secrets Manager for credentials
- CloudWatch for logging and metrics

**Option 2: Azure**
- Azure Function (HTTP Trigger) → Service Bus → Azure Function
- Key Vault for credentials
- Application Insights for monitoring

**Option 3: GCP**
- Cloud Functions (HTTP) → Pub/Sub → Cloud Run
- Secret Manager for credentials
- Cloud Logging and Monitoring

**Option 4: Custom/MCP (Future)**
- Custom webhook receiver
- Message queue implementation
- MCP-based function execution
- Pluggable monitoring and logging

---

## ✅ Success Criteria

### Function-Level Success Criteria

**Input Validation:**
- ✅ All required fields present
- ✅ Repository name is kebab-case
- ✅ Code type is supported
- ✅ No reserved names used

**Repository Creation:**
- ✅ Repository created on GitHub
- ✅ Visibility set correctly
- ✅ Description added
- ✅ Default branch is 'main'

**Branch Protection:**
- ✅ Protection rules applied to main branch
- ✅ Required reviewers configured
- ✅ Force push disabled

**Template Application:**
- ✅ README.md committed
- ✅ .gitignore committed
- ✅ Templates match code type

**JIRA Update:**
- ✅ Comment added with repository URL
- ✅ Custom field updated
- ✅ Labels added

### End-to-End Success Criteria

**Overall Process:**
- ✅ Complete within 30 seconds (90% of cases)
- ✅ Success rate > 95%
- ✅ All errors logged and reported
- ✅ JIRA ticket always updated (success or failure)
- ✅ No data loss (messages retained in queue)

---

## 📊 Monitoring & Alerting

### Key Metrics

**Success Metrics:**
- Repository creation success rate (target: >95%)
- Average processing time (target: <20 seconds)
- Repositories created per day/week/month

**Failure Metrics:**
- Repository creation failure rate (alert if >5%)
- DLQ message count (alert if >0)
- Retry count per message (alert if avg >1)

**Performance Metrics:**
- GitHub API response time
- JIRA API response time
- Function execution duration
- Queue depth (alert if >100)

### Alerts

**Critical Alerts:**
- DLQ message count > 0
- Failure rate > 10% (in 5-minute window)
- Function execution timeout
- Queue depth > 500 messages

**Warning Alerts:**
- Failure rate > 5%
- Average processing time > 30 seconds
- GitHub API rate limit > 80%
- Queue depth > 100 messages

---

## 🚀 Future Enhancements

### Phase 2 Enhancements

**1. Advanced Templates:**
- Custom template repository support
- Template versioning
- Dynamic template selection based on team/project

**2. Repository Configuration:**
- Custom branch protection rules per project
- Team-based access control
- Automated collaborator assignment

**3. CI/CD Integration:**
- Automatic GitHub Actions workflow setup
- Integration with Jenkins/CircleCI
- Automated pipeline configuration

**4. Compliance & Governance:**
- Security scanning setup (Snyk, Dependabot)
- License compliance checks
- SBOM generation

### MCP Integration (Future)

**Model Context Protocol (MCP) Benefits:**
- Pluggable function execution
- Hot-reload of function logic
- Multi-language support
- Custom runtime environments
- Advanced orchestration capabilities

**Potential MCP Architecture:**
```
JIRA Webhook → MCP Server → Function Registry → Core Functions
                    ↓
              Message Queue
                    ↓
         MCP Client (Executor)
```

---

## 📝 Summary

### Architecture Highlights

**Clear Separation:**
- ✅ Infrastructure (Black Box) - Flexible implementation
- ✅ Business Logic (Core Functions) - Focus of development

**Core Functions (10 Total):**
1. Input Validation
2. Repository Existence Check
3. GitHub Repository Creation
4. Branch Protection Setup
5. Template Selection & Generation
6. File Commit
7. Topics/Tags Management
8. JIRA Update (Success)
9. Error Handling
10. Logging & Monitoring

**Key Benefits:**
- ✅ Modular design - Easy to test and maintain
- ✅ Technology agnostic - Can run on any serverless platform
- ✅ Future-proof - Ready for MCP integration
- ✅ Reliable - Built-in retry and error handling
- ✅ Observable - Comprehensive logging and metrics

---

**End of Final Architecture Document**

> **Next Steps:**
> 1. Review and approve this architecture
> 2. Create detailed black box implementation (AWS/Azure/GCP)
> 3. Implement Phase 1: Core functions with local testing
> 4. Deploy to production environment



