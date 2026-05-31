# Default Branch Change - Conditional Form Architecture

## Overview

Unified automation system using a single JIRA form with conditional field visibility. The form dynamically shows different fields based on whether the request is for repository creation or default branch change.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         JIRA SERVICE DESK                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────┐            │
│  │  Single Unified Form                                    │            │
│  │  ───────────────────                                    │            │
│  │                                                          │            │
│  │  Request Type*: [Dropdown]                              │            │
│  │    ○ Repository Creation                                │            │
│  │    ○ Default Branch Change                              │            │
│  │                                                        │            │
│  │  ┌─────────────────────────────────────────────┐       │            │
│  │  │ IF "Repository Creation" selected:          │       │            │
│  │  │ ─────────────────────────────────           │       │            │
│  │  │ • Repository Name*                          │       │            │
│  │  │ • GitHub Organization*                      │       │            │
│  │  │ • Repository Type*                          │       │            │
│  │  │ • Code Type*                                │       │            │
│  │  │ • Description*                              │       │            │
│  │  │ • VP Name*                                  │       │            │
│  │  │ • Director Name*                            │       │            │
│  │  │ • Engineering Manager*                      │       │            │                            │       │            │
│  │  │ • Department*                               │       │            │
│  │  └─────────────────────────────────────────────┘       │            │
│  │                                                        │            │
│  │  ┌─────────────────────────────────────────────┐       │            │
│  │  │ IF "Default Branch Change" selected:        │       │            │
│  │  │ ─────────────────────────────────           │       │            │
│  │  │ • Repository Name*                          │       │            │
│  │  │ • GitHub Organization*                      │       │            │
│  │  │ • Current Default Branch*                   │       │            │
│  │  │ • New Default Branch*                       │       │            │
│  │  │ • VP Name*                                  │       │            │
│  │  │ • Director Name*                            │       │            │
│  │  │ • Engineering Manager*                      │       │            │
│  │  └─────────────────────────────────────────────┘       │            │
│  └────────────────────────────────────────────────────────┘            │
│                              │                                           │
│                              │ Submit                                    │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────┐            │
│  │         JIRA Automation Rule                            │            │
│  │  ───────────────────────                                │            │
│  │  Trigger: Issue Created                                 │            │
│  │  Action: Send to AWS SQS                                │            │
│  │                                                          │            │
│  │  Payload Logic:                                         │            │
│  │  IF request_type = "Repository Creation"                │            │
│  │    → "action_type": "create_repository"                 │            │
│  │  ELSE IF request_type = "Default Branch Change"         │            │
│  │    → "action_type": "change_branch"                     │            │
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
│  │  4. Check "action_type" field in message                │            │
│  │     ├─ "create_repository" → _process_repo_creation()  │            │
│  │     └─ "change_branch" → _process_branch_change() NEW  │            │
│  │                                                          │            │
│  │  _process_branch_change():                              │            │
│  │  5. Validate repository exists                          │            │
│  │  6. Validate current default branch matches             │            │
│  │  7. Validate new default branch exists in repo          │            │
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

### ✅ Best User Experience
- **Single Entry Point**: Users only need to know one place to go
- **Intuitive Interface**: Form dynamically adapts to user selection
- **Reduced Confusion**: No need to choose between different ticket types
- **Consistent Navigation**: Same portal, same process every time

### ✅ Minimal Infrastructure
- **No New Resources**: Uses existing Lambda, SQS queue, and DLQ
- **No Additional Costs**: Same AWS resources handle both operations
- **Simplified Architecture**: Single service to deploy and manage

### ✅ Code Reuse
- **Shared Libraries**: GitHub client, JIRA client, validators all shared
- **No Duplication**: Authentication, secret management, logging reused
- **Single Deployment**: Package and deploy once for both features

### ✅ JIRA Administration Efficiency
- **Single Form**: Only one form to create and maintain in JIRA
- **Single Automation Rule**: One rule with conditional logic
- **Centralized Configuration**: All changes in one place

### ✅ Quick Implementation
- **Fast to Deploy**: Add conditional logic + new function (~3-4 hours)
- **No Infrastructure Changes**: No Terraform updates needed
- **Minimal Testing**: Leverage existing test infrastructure

### ✅ Flexibility
- **Easy to Extend**: Add more request types (archive, delete, etc.) easily
- **Scalable Pattern**: Conditional form pattern works for many operations
- **Future-Proof**: Can add new fields without creating new forms

---

## Cons

### ❌ JIRA Form Complexity
- **Conditional Logic**: More complex form configuration in JIRA
- **Testing Overhead**: Need to test all field combinations
- **Maintenance**: Conditional rules can be fragile and hard to debug
- **Documentation**: Users need clear instructions on which option to choose

### ❌ Mixed Responsibilities
- **Single Responsibility Violation**: Lambda handles multiple distinct operations
- **Growing Complexity**: Function size grows with each new feature
- **Cognitive Load**: Developers need to understand entire codebase

### ❌ Validation Complexity
- **Conditional Validation**: Different fields required based on request type
- **Error Messages**: Need clear messaging for each scenario
- **Schema Management**: Multiple validation schemas in one system

### ❌ Tight Coupling
- **Shared Failure**: Bug in branch logic could affect repo creation
- **Deployment Risk**: Single deployment affects all operations
- **Version Management**: Can't deploy branch changes independently

### ❌ User Learning Curve
- **Decision Point**: Users must understand when to select which option
- **Field Overload**: Seeing all possible fields (even hidden) can be overwhelming
- **Help Documentation**: Need comprehensive guide explaining each option

### ❌ Testing Complexity
- **Broader Test Coverage**: Need to test all form configurations
- **Regression Risk**: Changes to one feature might break another
- **End-to-End Testing**: More complex user flow scenarios

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
- **Forms**: 1 form (modified with conditional fields)
- **Automation Rule**: 1 rule (modified with conditional payload logic)
- **Custom Fields**: 2-3 new fields (`request_type`, `current_default_branch`, `new_default_branch`)


---

## When to Use This Architecture

### ✅ Use This When:
- Want best user experience (single entry point)
- Infrastructure costs/complexity are a concern
- Users prefer simple, unified workflow
- Team is comfortable with JIRA conditional forms
- Plan to add more request types in the future
- Need quick implementation (within a day)
- Want to minimize JIRA administration overhead

### ❌ Don't Use This When:
- JIRA conditional forms are too complex for your team
- Users struggle with dropdown/conditional interfaces
- Need strict separation of concerns
- Want independent deployment for each feature
- JIRA admin team prefers separate forms
- Form has too many fields (becomes unwieldy)

---

## JIRA Form Configuration

### Conditional Field Logic

**Request Type Field:**
```
Field Type: Single Select Dropdown
Options:
  - Repository Creation
  - Default Branch Change
Required: Yes
```

**Conditional Fields - Repository Creation:**
```
Show when: Request Type = "Repository Creation"

Fields:
  - Repository Name (text, required)
  - GitHub Organization (select, required)
  - Repository Type (select: Private/Internal/Public, required)
  - Code Type (select: Java/Python/Nodejs/etc., required)
  - Description (multi-line text, required)
  - VP Name (user picker, required)
  - Director Name (user picker, required)
  - Engineering Manager (user picker, required)
  - Product Line (select, required)
  - Department (select, required)
```

**Conditional Fields - Default Branch Change:**
```
Show when: Request Type = "Default Branch Change"

Fields:
  - Repository Name (text, required)
  - GitHub Organization (select, required)
  - Current Default Branch (text, required)
  - New Default Branch (text, required, default: "main")
  - VP Name (user picker, required)
  - Director Name (user picker, required)
  - Engineering Manager (user picker, required)
```

