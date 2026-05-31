# Default Branch Change - Hybrid Architecture (Shared Lambda)

## Overview

Hybrid automation system that extends the existing repository creation Lambda to handle default branch changes using the same infrastructure and codebase. In this architecture the jira form will be new and the triggering rule will also be new. But the aws infrastructure will be existing one which we have used for repository creation.

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
│  │  • GitHub Organization*                                 │            │
│  │  • Current Default Branch*                              │            │
│  │  • New Default Branch*                                  │            │
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
│  │  Payload: Includes "action_type": "change_branch"       │            │
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
│  │  SQS Queue (SHARED - Existing)                          │            │
│  │  ──────────────────────────                             │            │
│  │  Name: github-repo-automation-test-queue                │            │
│  │  Type: Standard                                         │            │
│  │  Retention: 14 days                                     │            │
│  │  Visibility Timeout: 360 seconds (6 minutes)            │            │
│  │  Max Receive Count: 3                                   │            │
│  │  Dead Letter Queue: github-repo-automation-test-dlq     │            │
│  │                                                          │            │
│  │  Handles:                                               │            │
│  │  • Repository creation messages                         │            │
│  │  • Default branch change messages                       │            │
│  └────────────────────────────────────────────────────────┘            │
│                              │                                           │
│                              │ Event Source Mapping (Existing)           │
│                              │ (Automatic trigger)                       │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────┐            │
│  │  Lambda Function (SHARED - Extended)                    │            │
│  │  ────────────────────────────                           │            │
│  │  Name: github-repo-automation-test-repo-creator         │            │
│  │  Runtime: Python 3.9                                    │            │
│  │  Timeout: 300 seconds (5 minutes)                       │            │
│  │  Memory: 512 MB                                         │            │
│  │  Handler: src.github_handler.lambda_handler             │            │
│  │                                                          │            │
│  │  Process:                                               │            │
│  │  1. Parse & validate SQS message                        │            │
│  │  2. Get GitHub App credentials (Secrets Manager)        │            │
│  │  3. Get JIRA credentials (Secrets Manager)              │            │
│  │  4. Check "action_type" field                           │            │
│  │     ├─ "create_repository" → _process_repo_creation()  │            │
│  │     └─ "change_branch" → _process_branch_change() NEW  │            │
│  │                                                          │            │
│  │  _process_branch_change():                              │            │
│  │  5. Validate repository exists                          │            │
│  │  6. Validate current default branch matches             │            │
│  │  7. Validate target branch exists in repo               │            │
│  │  8. Change default branch via GitHub API                │            │
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
│  │  (SHARED)   │  │  (SHARED)        │  │  (SHARED)       │           │
│  │             │  │                  │  │                 │           │
│  │  • GitHub   │  │  Log Group:      │  │  • Invocations  │           │
│  │    App ID   │  │  /aws/lambda/    │  │  • Duration     │           │
│  │  • Private  │  │  github-repo-    │  │  • Errors       │           │
│  │    Key      │  │  automation-     │  │  • Success Rate │           │
│  │  • JIRA     │  │  test-repo-      │  │                 │           │
│  │    Creds    │  │  creator         │  │  Metrics by:    │           │
│  │             │  │                  │  │  • action_type  │           │
│  │             │  │  Retention:      │  │                 │           │
│  │             │  │  7 days          │  │                 │           │
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
│  │  • Create Repository     │          │                          │    │
│  │                          │          │  Authentication:         │    │
│  │  Authentication:         │          │  Basic Auth (API Token)  │    │
│  │  GitHub App (JWT)        │          │                          │    │
│  └──────────────────────────┘          └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Pros

### ✅ Minimal Infrastructure
- **No New Resources**: Uses existing Lambda, SQS queue, and DLQ
- **No Additional Costs**: Same AWS resources handle both operations
- **Simplified Architecture**: Single service to deploy and manage

### ✅ Code Reuse
- **Shared Libraries**: GitHub client, JIRA client, validators all shared
- **No Duplication**: Authentication, secret management, logging reused
- **Single Deployment**: Package and deploy once for both features

### ✅ Quick Implementation
- **Fast to Deploy**: Add new function to existing code (~2-3 hours)
- **No Infrastructure Changes**: No Terraform updates needed
- **Minimal Testing**: Leverage existing test infrastructure

### ✅ Unified Monitoring
- **Single Dashboard**: Monitor both operations in one place
- **Consolidated Logs**: All operations in same CloudWatch log group
- **Simple Alerting**: One set of alarms for both features

### ✅ Operational Simplicity
- **Single Point of Management**: One Lambda to maintain and update
- **Easier Troubleshooting**: All logic in one codebase
- **Consistent Patterns**: Same error handling, retry logic, logging

### ✅ Flexibility
- **Easy to Extend**: Add more operations (archive, delete, etc.) easily
- **Action-Based Routing**: Clean pattern for adding new features
- **Gradual Enhancement**: Start simple, add complexity as needed

---

## Cons

### ❌ Mixed Responsibilities
- **Single Responsibility Violation**: Lambda handles multiple distinct operations
- **Growing Complexity**: Function size grows with each new feature
- **Cognitive Load**: Developers need to understand entire codebase

### ❌ Tight Coupling
- **Shared Failure**: Bug in branch logic could affect repo creation
- **Deployment Risk**: Single deployment affects all operations
- **Version Management**: Can't deploy branch changes independently

### ❌ Testing Complexity
- **Broader Test Coverage**: Need to test all code paths together
- **Regression Risk**: Changes to one feature might break another
- **Integration Testing**: More complex test scenarios required

### ❌ Performance Considerations
- **Growing Cold Start**: Larger codebase means slower Lambda cold starts
- **Memory Usage**: Single function needs enough memory for all operations
- **Package Size**: Deployment package grows with each feature

### ❌ Debugging Challenges
- **Log Noise**: Both operations log to same stream, harder to filter
- **Metric Ambiguity**: Need custom dimensions to separate operation types
- **Error Attribution**: Harder to identify which operation caused failure

---

## Resource Requirements

### AWS Resources (NO NEW RESOURCES)
- **Lambda Function**: Existing (`github-repo-automation-test-repo-creator`)
- **SQS Queue**: Existing (`github-repo-automation-test-queue`)
- **DLQ**: Existing (`github-repo-automation-test-dlq`)
- **Event Source Mapping**: Existing (no changes)
- **IAM Role**: Existing (no permission changes needed)
- **CloudWatch Log Group**: Existing (shared logs)
- **Secrets Manager**: Existing (shared secrets)

### JIRA Resources
- **Automation Rule**: 1 new rule (for branch change work type)
- **Work Type**: 1 new option ("Default Branch Change")
- **Custom Fields**: 1-2 new fields (`current_default_branch`, `new_default_branch`)


- **NoteThis is completely new form**

### Code Changes
- **New Files**:
  - `src/branch_operations.py` (branch change logic)
  - `src/validators.py` (add BranchChangeInput model)
- **Modified Files**:
  - `src/github_handler.py` (add routing logic)
  - `src/jira_client.py` (add branch change JIRA comments)


---



## When to Use This Architecture

### ✅ Use This When:
- Want fastest time to market (hours vs days)
- Infrastructure costs/complexity are a concern
- Branch changes are low volume (< 100/month)
- Team is small with limited DevOps resources
- Need simple, maintainable solution
- Plan to add more operations later (archive, delete, etc.)

### ❌ Don't Use This When:
- Need strict separation of concerns
- Branch operations are complex and evolving independently
- High volume of branch changes (> 1000/month)
- Want independent scaling for each operation
- Team prefers microservices architecture
- Need to deploy branch changes without affecting repo creation

---

