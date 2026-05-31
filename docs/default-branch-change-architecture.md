# Default Branch Change Automation - Architecture

## Overview

Dedicated automation system for changing the default branch of existing GitHub repositories through JIRA self-service workflow. In this architecture, we are creating a new jira form and new triggering rule for the same.The aws infrastructure will also be new.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         JIRA SERVICE DESK                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────┐            │
│  │  Work Type: Default Branch Change                       │            │
│  │  ─────────────────────────────────                      │            │
│  │  • Repository Name*                                     │            │
│  │  • GitHub Organization*                                 │
│  │  • Current Default Branch*                              │            │
│  │  • Target Default Branch*                               │            │
│  │  • VP Name*                                             │            │
│  │  • Director Name*                                       │            │
│  │  • Engineering Manager*                                 │            │
│  └────────────────────────────────────────────────────────┘            │
│                              │                                           │
│                              │ Submit                                    │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────┐            │
│  │         JIRA Automation Rule                            │            │
│  │  ───────────────────────                                │            │
│  │  Trigger: Issue Created                                 │            │
│  │  Condition: Work Type = "Default Branch Change"         │            │
│  │  Action: Send to AWS SQS                                │            │
│  └────────────────────────────────────────────────────────┘            │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   │ HTTPS POST
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            AWS CLOUD                                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────┐            │
│  │  SQS Queue                                              │            │
│  │  ──────────                                             │            │
│  │  Name: github-branch-change-queue                       │            │
│  │  Type: Standard                                         │            │
│  │  Retention: 14 days                                     │            │
│  │  Visibility Timeout: 360 seconds (6 minutes)            │            │
│  │  Max Receive Count: 3                                   │            │
│  │  Dead Letter Queue: github-branch-change-dlq            │            │
│  └────────────────────────────────────────────────────────┘            │
│                              │                                           │
│                              │ Event Source Mapping                      │
│                              │ (Automatic trigger)                       │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────┐            │
│  │  Lambda Function                                        │            │
│  │  ──────────────                                         │            │
│  │  Name: github-branch-change-handler                     │            │
│  │  Runtime: Python 3.9                                    │            │
│  │  Timeout: 300 seconds (5 minutes)                       │            │
│  │  Memory: 512 MB                                         │            │
│  │  Handler: src.branch_handler.lambda_handler             │            │
│  │                                                          │            │
│  │  Process:                                               │            │
│  │  1. Parse & validate SQS message                        │            │
│  │  2. Get GitHub App credentials (Secrets Manager)        │            │
│  │  3. Authenticate with GitHub API                        │            │
│  │  4. Get repository details                              │            │
│  │  5. Validate current default branch                     │            │
│  │  6. Validate target branch exists                       │            │
│  │  7. Change default branch via GitHub API                │            │
│  │  8. Get JIRA credentials (Secrets Manager)              │            │
│  │  9. Update JIRA ticket with result                      │            │
│  │  10. Transition ticket to "Done"                         │            │
│  └────────────────────────────────────────────────────────┘            │
│                              │                                           │
│                              │                                           │
│         ┌────────────────────┼────────────────────┐                     │
│         │                    │                    │                     │
│         ▼                    ▼                    ▼                     │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────┐           │
│  │  Secrets    │  │  CloudWatch      │  │  CloudWatch     │           │
│  │  Manager    │  │  Logs            │  │  Metrics        │           │
│  │  ─────────  │  │  ────            │  │  ───────        │           │
│  │  • GitHub   │  │  Log Group:      │  │  • Invocations  │           │
│  │    App ID   │  │  /aws/lambda/    │  │  • Duration     │           │
│  │  • Private  │  │  github-branch-  │  │  • Errors       │           │
│  │    Key      │  │  change-handler  │  │  • Success Rate │           │
│  │  • JIRA     │  │                  │  │                 │           │
│  │    Creds    │  │  Retention:      │  │                 │
│  │             │  │  7 days          │  │                 │
│  └─────────────┘  └──────────────────┘  └─────────────────┘           │
│                                                                          │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   │ HTTPS API Calls
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                                   │
│                                                                          │
│  ┌──────────────────────────┐          ┌──────────────────────────┐    │
│  │  GitHub API              │          │  JIRA API                │    │
│  │  ──────────              │          │  ────────                │    │
│  │  Operations:             │          │  Operations:             │    │
│  │  • Get Repository        │          │  • Get Issue             │    │
│  │  • Get Branch            │          │  • Add Comment           │    │
│  │  • Update Default Branch │          │  • Transition Issue      │    │
│  │                          │          │                          │    │
│  │  Authentication:         │          │  Authentication:         │    │
│  │  GitHub App (JWT)        │          │  Basic Auth (API Token)  │    │
│  └──────────────────────────┘          └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Pros

### ✅ Separation of Concerns
- **Single Responsibility**: Dedicated to branch management only
- **Clear Purpose**: No confusion with repository creation
- **Maintainable**: Isolated codebase, easier to debug and enhance

### ✅ Scalability
- **Extensible**: Easy to add more branch operations (branch protection, policies, etc.)
- **Independent Deployment**: Deploy branch changes without affecting repo creation
- **Dedicated Resources**: Own SQS queue, Lambda, and DLQ

### ✅ User Experience
- **Dedicated JIRA Form**: Clear, focused workflow for branch changes
- **No Confusion**: Different work type prevents mixing with repo creation
- **Targeted Fields**: Only asks for relevant information

### ✅ Observability
- **Isolated Metrics**: Dedicated CloudWatch metrics for branch operations
- **Clear Logging**: Separate log group for easy troubleshooting
- **Independent Monitoring**: Set up alerts specific to branch operations

### ✅ Security
- **Least Privilege**: Lambda only needs branch update permissions
- **Audit Trail**: Separate logs for compliance and auditing
- **Failure Isolation**: Branch change failures don't affect repo creation

### ✅ Reliability
- **Independent DLQ**: Failed branch changes go to dedicated dead letter queue
- **Retry Mechanism**: 3 attempts before moving to DLQ
- **No Cross-Impact**: Issues in branch changes don't affect repo creation service

---

## Cons

### ❌ Infrastructure Overhead
- **Additional Resources**: New Lambda function, SQS queue, and DLQ
- **More Costs**: Additional AWS charges (though minimal for low volume)
- **Deployment Complexity**: Separate Terraform modules and deployments

### ❌ Maintenance Burden
- **Multiple Codebases**: Need to maintain separate Lambda functions
- **Coordination**: Updates to shared libraries (github_client, jira_client) affect both
- **Testing**: Need separate test suites for each service

### ❌ Code Duplication
- **Shared Logic**: GitHub App authentication, JIRA integration duplicated
- **Common Libraries**: Need to package same dependencies in both Lambdas
- **Secret Management**: Both services access same secrets (though read-only)

### ❌ JIRA Management
- **Multiple Workflows**: Users need to know which work type to choose
- **Additional Configuration**: New automation rule to set up and maintain
- **Form Management**: More JIRA custom fields and forms to manage

### ❌ Monitoring Complexity
- **Multiple Dashboards**: Need to monitor two separate Lambda functions
- **Alert Sprawl**: More CloudWatch alarms to configure and manage
- **Debugging**: Issues might span multiple services

### ❌ Initial Setup Time
- **New Infrastructure**: ~4-8 hours to deploy and test
- **JIRA Configuration**: ~2-3 hours to set up automation and forms
- **Documentation**: Additional docs for new workflow

---

## Resource Requirements

### AWS Resources
- **Lambda Function**: 1 new function (`github-branch-change-handler`)
- **SQS Queues**: 2 new queues (main + DLQ)
- **Event Source Mapping**: 1 new mapping (SQS → Lambda)
- **IAM Role**: 1 new role with policies
- **CloudWatch Log Group**: 1 new log group
- **Secrets Manager**: Shared (existing secrets)

### JIRA Resources
- **Automation Rule**: 1 new rule
- **Work Type**: 1 new option ("Default Branch Change")
- **Custom Fields**: 0-2 new fields (if needed)



---



## When to Use This Architecture

### ✅ Use This When:
- Need dedicated branch management operations
- Planning to add more branch features (protection rules, policies)
- Want clear separation between creation and management
- Have resources for maintaining multiple services
- Expect high volume of branch changes

### ❌ Don't Use This When:
- Branch changes are rare (< 10/month)
- Want minimal infrastructure
- Team is small with limited DevOps resources
- Need quick implementation (use Option 1 instead)
- Cost optimization is critical

---

