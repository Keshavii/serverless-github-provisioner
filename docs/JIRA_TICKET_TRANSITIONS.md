# JIRA Ticket Transitions - Implementation Plan

> **Status:** 📋 PLANNED - Not yet implemented  
> **Priority:** HIGH (Success transitions) / MEDIUM (Failure handling)  
> **Prerequisites:** JIRA access for testing

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Current Behavior](#current-behavior)
3. [Proposed Enhancements](#proposed-enhancements)
4. [Configuration Options](#configuration-options)
5. [Implementation Plan](#implementation-plan)
6. [Error Categorization](#error-categorization)
7. [Testing Guide](#testing-guide)
8. [Rollback Plan](#rollback-plan)

---

## 📖 Overview

### What This Enhancement Does

Currently, the system only adds **comments and labels** to JIRA tickets. This enhancement will:

✅ **Automatically transition tickets** to appropriate statuses based on outcomes  
✅ **Categorize failures** and route them to the right team/person  
✅ **Reduce manual work** by auto-closing successful tickets  
✅ **Improve metrics** with accurate workflow tracking  

### Why This Matters

- **For Users:** No need to manually close tickets after successful repo creation
- **For Platform Team:** Failed tickets automatically routed to the right people
- **For Metrics:** Accurate cycle time and throughput measurements
- **For Audit:** Complete workflow history in JIRA

---

## 🔍 Current Behavior

### What Happens Today

| Event | Comment Added? | Labels Added? | Status Changed? |
|-------|---------------|---------------|-----------------|
| **Repository created successfully** | ✅ Yes | ✅ Yes (`repository-created`, `automated`) | ❌ No - stays in current status |
| **Repository creation failed** | ✅ Yes | ✅ Yes (`repository-creation-failed`, `automated`) | ❌ No - stays in current status |

### Problems with Current Approach

1. ❌ Tickets remain "In Progress" even after successful completion
2. ❌ Failed tickets don't get routed back to users for corrections
3. ❌ No distinction between different types of failures
4. ❌ Manual work required to close hundreds of tickets
5. ❌ Metrics are inaccurate (tickets never "complete")

---

## ✨ Proposed Enhancements

### Phase 1: Success Transitions (HIGH PRIORITY)

**Goal:** Automatically move tickets to "Done" when repository is created successfully

**Behavior:**
```
Repository Created Successfully
    ↓
Add success comment + labels (existing)
    ↓
Transition ticket to "Done" (NEW)
    ↓
Set resolution to "Done" if required (NEW)
```

**Configuration:**
- Enable/disable via `AUTO_TRANSITION_ON_SUCCESS=true/false`
- Configurable target status name (e.g., "Done", "Completed", "Closed")
- Configurable resolution (if workflow requires it)

---

### Phase 2: Categorized Failure Handling (MEDIUM PRIORITY)

**Goal:** Route failures to appropriate teams based on error type

**Failure Categories:**

#### 1. **Validation Failures** (User Error)
**Examples:**
- Invalid repository name format
- Missing required fields
- Invalid organization name

**Action:**
- Status: `Needs Information` or `Backlog`
- Assignee: Assign back to reporter
- Rationale: User needs to fix and resubmit

#### 2. **Permission/Authentication Failures** (Config Error)
**Examples:**
- GitHub token expired
- No admin access to organization
- JIRA credentials invalid

**Action:**
- Status: `Blocked` or `Waiting for Support`
- Assignee: Assign to platform team
- Label: `platform-team-action-required`
- Rationale: Admin/infrastructure fix needed

#### 3. **Transient Failures** (Temporary Issues)
**Examples:**
- Network timeout
- GitHub API rate limiting
- JIRA API temporarily unavailable

**Action:**
- Status: Keep in `In Progress` (don't change)
- Label: `auto-retry-scheduled`
- Rationale: System will retry automatically

#### 4. **Business Rule Failures**
**Examples:**
- Repository already exists (idempotent case)
- Duplicate request
- Quota exceeded

**Action:**
- **If repo exists:** Transition to `Done` (goal achieved)
- **If quota exceeded:** Transition to `Blocked` (needs approval)
- **If duplicate:** Transition to `Duplicate` or `Won't Do`

---

## ⚙️ Configuration Options

### Environment Variables to Add

Add these to your `.env` file:

```bash
# ============================================
# JIRA Ticket Transition Configuration
# ============================================

# --- Success Handling ---
AUTO_TRANSITION_ON_SUCCESS=true
SUCCESS_TRANSITION_NAME=Done
SUCCESS_RESOLUTION=Done  # Required by some JIRA workflows

# --- Failure Handling ---
AUTO_TRANSITION_ON_FAILURE=true
FAILURE_STRATEGY=categorized  # Options: categorized, blocked, none

# --- Categorized Failure Transitions ---
VALIDATION_FAILURE_STATUS=Needs Information
PERMISSION_FAILURE_STATUS=Blocked
TRANSIENT_FAILURE_STATUS=In Progress  # Don't change
BUSINESS_RULE_FAILURE_STATUS=Blocked

# --- Assignee Management ---
ASSIGN_BACK_TO_REPORTER_ON_VALIDATION_FAILURE=true
ASSIGN_TO_PLATFORM_TEAM_ON_PERMISSION_FAILURE=true
PLATFORM_TEAM_JIRA_USER=platform-team-bot

# --- Retry Configuration (for transient failures) ---
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0
```

### Configuration in `src/config.py`

Add these fields to the `Settings` class:

```python
# JIRA Transition Configuration
auto_transition_on_success: bool = Field(
    default=True,
    description="Auto-transition tickets to Done on success"
)
success_transition_name: str = Field(
    default="Done",
    description="Target status for successful tickets"
)
success_resolution: Optional[str] = Field(
    default="Done",
    description="Resolution to set (if required by workflow)"
)

auto_transition_on_failure: bool = Field(
    default=True,
    description="Auto-transition tickets on failure"
)
failure_strategy: str = Field(
    default="categorized",
    description="Failure handling strategy"
)

# Categorized failure statuses
validation_failure_status: str = Field(
    default="Needs Information",
    description="Status for validation failures"
)
permission_failure_status: str = Field(
    default="Blocked",
    description="Status for permission failures"
)
transient_failure_status: str = Field(
    default="In Progress",
    description="Status for transient failures"
)
business_rule_failure_status: str = Field(
    default="Blocked",
    description="Status for business rule failures"
)

# Assignee management
assign_back_to_reporter_on_validation_failure: bool = Field(
    default=True,
    description="Assign back to reporter on validation failure"
)
assign_to_platform_team_on_permission_failure: bool = Field(
    default=True,
    description="Assign to platform team on permission failure"
)
platform_team_jira_user: str = Field(
    default="platform-team-bot",
    description="JIRA username for platform team"
)
```

---

## 🛠️ Implementation Plan

### Step 1: Add Configuration (15 minutes)

1. ✅ Update `.env` with new configuration options
2. ✅ Update `src/config.py` with new settings fields
3. ✅ Add field validators if needed

### Step 2: Implement Success Transition (45 minutes)

Create new function in `src/jira_client.py`:

```python
def transition_ticket_on_success(
    ticket_id: str,
    repo_data: Dict,
    correlation_id: str = None
) -> bool:
    """
    Transition ticket to 'Done' state after successful repository creation.

    Args:
        ticket_id: JIRA ticket ID
        repo_data: Repository data from GitHub
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if transition succeeded, False otherwise (best-effort)
    """
    settings = get_settings()

    # Check if auto-transition is enabled
    if not settings.auto_transition_on_success:
        log_and_monitor(
            "ticket_transition_skipped",
            level="INFO",
            correlation_id=correlation_id,
            reason="auto_transition_disabled"
        )
        return False

    try:
        client = JiraClient()

        # Get available transitions for this ticket
        transitions = client.client.transitions(ticket_id)

        # Find the target transition
        target_transition = None
        for t in transitions:
            if t['name'].lower() == settings.success_transition_name.lower():
                target_transition = t['id']
                break

        if not target_transition:
            log_and_monitor(
                "transition_not_found",
                level="WARNING",
                correlation_id=correlation_id,
                ticket_id=ticket_id,
                target_status=settings.success_transition_name,
                available_transitions=[t['name'] for t in transitions]
            )
            return False

        # Prepare transition fields (some workflows require resolution)
        transition_fields = {}
        if settings.success_resolution:
            transition_fields['resolution'] = {
                'name': settings.success_resolution
            }

        # Execute the transition
        client.client.transition_issue(
            ticket_id,
            target_transition,
            fields=transition_fields if transition_fields else None
        )

        log_and_monitor(
            "ticket_transitioned_to_done",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            new_status=settings.success_transition_name,
            repo_name=repo_data.get('name')
        )

        return True

    except Exception as e:
        # Best-effort: log warning but don't fail
        log_and_monitor(
            "ticket_transition_failed",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
        return False
```

**Update `update_jira_success()` to call this:**

```python
def update_jira_success(
    ticket_id: str, repo_data: Dict, correlation_id: str = None
) -> bool:
    # ... existing code for comment and labels ...

    # NEW: Transition ticket to Done
    transition_ticket_on_success(ticket_id, repo_data, correlation_id)

    return True
```

---

### Step 3: Implement Failure Categorization (60 minutes)

Create new function in `src/jira_client.py`:

```python
def transition_ticket_on_failure(
    ticket_id: str,
    error_type: str,  # "validation", "permission", "transient", "business_rule"
    error_message: str,
    correlation_id: str = None
) -> bool:
    """
    Transition ticket based on failure type.

    Args:
        ticket_id: JIRA ticket ID
        error_type: Type of failure (validation/permission/transient/business_rule)
        error_message: Error message
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if transition succeeded
    """
    settings = get_settings()

    if not settings.auto_transition_on_failure:
        return False

    if settings.failure_strategy == "none":
        return False

    # Determine target status based on error type
    status_mapping = {
        "validation": settings.validation_failure_status,
        "permission": settings.permission_failure_status,
        "transient": settings.transient_failure_status,
        "business_rule": settings.business_rule_failure_status,
    }

    target_status = status_mapping.get(error_type)

    if not target_status or target_status == "In Progress":
        # Don't transition if configured to stay in current state
        return False

    try:
        client = JiraClient()

        # Get available transitions
        transitions = client.client.transitions(ticket_id)

        # Find matching transition
        target_transition = None
        for t in transitions:
            if t['name'].lower() == target_status.lower():
                target_transition = t['id']
                break

        if not target_transition:
            log_and_monitor(
                "transition_not_found",
                level="WARNING",
                ticket_id=ticket_id,
                target_status=target_status,
                error_type=error_type
            )
            return False

        # Execute transition
        client.client.transition_issue(ticket_id, target_transition)

        # Handle assignee changes
        _handle_assignee_on_failure(client, ticket_id, error_type, settings)

        log_and_monitor(
            "ticket_transitioned_on_failure",
            level="INFO",
            ticket_id=ticket_id,
            error_type=error_type,
            new_status=target_status
        )

        return True

    except Exception as e:
        log_and_monitor(
            "ticket_transition_failed",
            level="WARNING",
            ticket_id=ticket_id,
            error=str(e)
        )
        return False


def _handle_assignee_on_failure(
    client: JiraClient,
    ticket_id: str,
    error_type: str,
    settings
) -> None:
    """Handle assignee changes based on error type."""

    try:
        issue = client.client.issue(ticket_id)

        if error_type == "validation" and settings.assign_back_to_reporter_on_validation_failure:
            # Assign back to reporter
            reporter = issue.fields.reporter.name
            issue.update(fields={'assignee': {'name': reporter}})

        elif error_type == "permission" and settings.assign_to_platform_team_on_permission_failure:
            # Assign to platform team
            issue.update(fields={'assignee': {'name': settings.platform_team_jira_user}})

    except Exception as e:
        log_and_monitor(
            "assignee_update_failed",
            level="WARNING",
            ticket_id=ticket_id,
            error=str(e)
        )
```

---

### Step 4: Error Categorization Logic (30 minutes)

Update your main orchestrator (Lambda handler or wherever errors are caught):

```python
def handle_repository_creation(event):
    """Main orchestration function."""

    ticket_id = event.get('ticket_id')
    correlation_id = str(uuid.uuid4())

    try:
        # Step 1: Validate input
        validated_data = validate_input(event, correlation_id)

    except ValidationError as e:
        # VALIDATION FAILURE
        update_jira_failure(ticket_id, str(e), correlation_id)
        transition_ticket_on_failure(ticket_id, "validation", str(e), correlation_id)
        raise

    try:
        # Step 2: Check if repo exists
        exists = check_repository_exists(
            validated_data['repo_name'],
            validated_data['github_org'],
            correlation_id
        )

        if exists:
            # BUSINESS RULE: Idempotent case
            repo_data = get_existing_repo_data(...)  # Fetch existing repo
            update_jira_success(ticket_id, repo_data, correlation_id)
            transition_ticket_on_success(ticket_id, repo_data, correlation_id)
            return {"status": "success", "message": "Repository already exists"}

        # Step 3: Create repository
        repo_data = create_github_repository(validated_data, correlation_id)

        # SUCCESS
        update_jira_success(ticket_id, repo_data, correlation_id)
        transition_ticket_on_success(ticket_id, repo_data, correlation_id)

        return {"status": "success", "repo_url": repo_data['html_url']}

    except GitHubAPIError as e:
        # Categorize GitHub errors
        if e.status_code in [401, 403]:
            # PERMISSION/AUTH FAILURE
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "permission", str(e), correlation_id)

        elif e.status_code == 422 and "already exists" in str(e).lower():
            # BUSINESS RULE: Repository already exists
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)

        elif e.status_code in [408, 429, 500, 502, 503, 504]:
            # TRANSIENT FAILURE - will retry
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "transient", str(e), correlation_id)
            # Trigger retry mechanism here

        else:
            # UNKNOWN FAILURE - treat as business rule
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)

        raise

    except Exception as e:
        # UNKNOWN ERROR
        update_jira_failure(ticket_id, str(e), correlation_id)
        transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)
        raise
```

---

## 📊 Error Categorization

### Decision Tree for Error Classification

```
Error Occurred
    │
    ├─→ ValidationError → "validation"
    │
    ├─→ GitHubAPIError
    │   │
    │   ├─→ status_code in [401, 403] → "permission"
    │   │
    │   ├─→ status_code == 422 AND "already exists" → "business_rule" (idempotent)
    │   │
    │   ├─→ status_code in [408, 429, 500, 502, 503, 504] → "transient"
    │   │
    │   └─→ Other status codes → "business_rule"
    │
    └─→ Other Exceptions → "business_rule"
```

### Error Type Mappings

| Error Type | HTTP Status Codes | Examples | Target Status | Assignee |
|------------|------------------|----------|---------------|----------|
| **validation** | N/A (pre-API) | Invalid repo name, missing fields | Needs Information | Reporter |
| **permission** | 401, 403 | Token expired, no org access | Blocked | Platform Team |
| **transient** | 408, 429, 500, 502, 503, 504 | Timeout, rate limit, server error | In Progress | (unchanged) |
| **business_rule** | 422, 409, others | Repo exists, quota exceeded | Blocked or Done | (unchanged) |

---

## 🧪 Testing Guide

### Prerequisites

1. ✅ JIRA access configured
2. ✅ Test JIRA project with appropriate workflow
3. ✅ Permissions to create/transition tickets

### Test Cases

#### Test 1: Success Transition

**Setup:**
1. Create a JIRA ticket manually (e.g., "TEST-001")
2. Set status to "In Progress"
3. Ensure "Done" transition is available

**Execute:**
```python
# Trigger repository creation with valid data
event = {
    "ticket_id": "TEST-001",
    "repo_name": "test-repo-success",
    "github_org": "Repo-Creation-Automation",
    # ... other valid fields
}
```

**Expected Result:**
- ✅ Repository created on GitHub
- ✅ JIRA comment added with success message
- ✅ Labels added: `repository-created`, `automated`
- ✅ **Ticket status changed to "Done"**
- ✅ Resolution set to "Done" (if configured)

---

#### Test 2: Validation Failure

**Setup:**
1. Create JIRA ticket "TEST-002"
2. Ensure "Needs Information" status exists

**Execute:**
```python
# Trigger with invalid repository name
event = {
    "ticket_id": "TEST-002",
    "repo_name": "Invalid_Name_With_Underscores",  # Should be kebab-case
    # ...
}
```

**Expected Result:**
- ✅ Repository NOT created
- ✅ JIRA comment with error details
- ✅ Label: `repository-creation-failed`
- ✅ **Status changed to "Needs Information"**
- ✅ **Assigned back to reporter**

---

#### Test 3: Permission Failure

**Setup:**
1. Use expired/invalid GitHub token
2. Create JIRA ticket "TEST-003"

**Execute:**
```python
# Use invalid token in environment
os.environ['GITHUB_TOKEN'] = 'invalid_token_xyz'
```

**Expected Result:**
- ✅ 403 error from GitHub
- ✅ JIRA comment with permission error
- ✅ **Status changed to "Blocked"**
- ✅ **Assigned to platform team**
- ✅ Label: `platform-team-action-required`

---

#### Test 4: Transient Failure Handling

**Setup:**
1. Simulate network timeout or rate limit

**Execute:**
```python
# Mock GitHub API to return 429 (rate limit)
```

**Expected Result:**
- ✅ JIRA comment about transient error
- ✅ **Status remains "In Progress"**
- ✅ Label: `auto-retry-scheduled`
- ✅ Retry mechanism triggered (if implemented)

---

#### Test 5: Repository Already Exists (Idempotent)

**Setup:**
1. Create repository manually first
2. Trigger automation with same name

**Execute:**
```python
# Attempt to create already-existing repo
```

**Expected Result:**
- ✅ Detection that repo exists
- ✅ JIRA comment with success (idempotent)
- ✅ **Status changed to "Done"**
- ✅ No error raised

---

### Manual Testing Checklist

- [ ] Verify all transitions exist in your JIRA workflow
- [ ] Test with `AUTO_TRANSITION_ON_SUCCESS=false` (should skip transitions)
- [ ] Test with non-existent target status name (should log warning)
- [ ] Verify assignee changes work correctly
- [ ] Check that labels are still added even if transition fails
- [ ] Confirm resolution is set only when required
- [ ] Test with workflow that doesn't require resolution
- [ ] Verify logging includes all correlation IDs

---

## 🔙 Rollback Plan

### If Issues Occur in Production

**Immediate Rollback:**
1. Set `AUTO_TRANSITION_ON_SUCCESS=false`
2. Set `AUTO_TRANSITION_ON_FAILURE=false`
3. Redeploy with these settings

**System will revert to:**
- ✅ Comments still added
- ✅ Labels still added
- ❌ No status transitions

**No data loss, fully backward compatible!**

---

## 📝 Implementation Checklist

### Phase 1: Configuration
- [ ] Add new environment variables to `.env`
- [ ] Update `src/config.py` with new settings
- [ ] Test configuration loading

### Phase 2: Success Transitions
- [ ] Implement `transition_ticket_on_success()`
- [ ] Update `update_jira_success()` to call new function
- [ ] Add comprehensive logging
- [ ] Test with real JIRA ticket

### Phase 3: Failure Handling
- [ ] Implement `transition_ticket_on_failure()`
- [ ] Implement `_handle_assignee_on_failure()`
- [ ] Update orchestrator with error categorization
- [ ] Test all failure scenarios

### Phase 4: Testing & Validation
- [ ] Run all test cases
- [ ] Verify workflow compatibility
- [ ] Check logs and monitoring
- [ ] Document any workflow-specific customizations

### Phase 5: Deployment
- [ ] Deploy to staging environment
- [ ] Monitor for 1-2 days
- [ ] Get user feedback
- [ ] Deploy to production
- [ ] Monitor closely for first week

---

## 🎯 Success Metrics

### After Implementation, Track:

1. **Automation Rate**
   - % of tickets auto-closed vs manually closed
   - Target: >90% auto-closed

2. **Accuracy**
   - % of tickets transitioned to correct status
   - Target: >95% accuracy

3. **Error Routing**
   - % of validation errors correctly sent back to reporter
   - % of permission errors correctly sent to platform team
   - Target: 100% correct routing

4. **Cycle Time**
   - Average time from "In Progress" to "Done"
   - Should decrease with automation

5. **Manual Intervention**
   - Number of tickets requiring manual status changes
   - Target: <5% need manual intervention

---

## 📚 Reporting & Analytics Using JIRA

### How to Track Repository Creation History in JIRA

JIRA will be your **single source of truth** for tracking all repository creation attempts (both successful and failed).

---

### 📋 **JIRA Custom Fields (Optional but Recommended)**

#### Why Add Custom Fields?

Currently, repository data is stored in **comments** (human-readable but requires parsing). Adding custom fields provides **structured, queryable data**.

#### Recommended Custom Fields:

| Field Name | Field Type | Description | Example Value |
|------------|-----------|-------------|---------------|
| **Repository Name** | Text Field (single line) | Name of the repository | `test-repo-001` |
| **Repository URL** | URL Field | GitHub repository URL | `https://github.com/Repo-Creation-Automation/test-repo-001` |
| **Repository ID** | Number Field | GitHub repository ID | `1195809474` |
| **GitHub Organization** | Text Field (single line) | Organization name | `Repo-Creation-Automation` |
| **Creation Status** | Single Select | Status of creation | `Success`, `Failed`, `In Progress` |

#### How to Create Custom Fields in JIRA:

1. Go to **JIRA Settings** → **Issues** → **Custom Fields**
2. Click **Create Custom Field**
3. Select field type (Text, URL, Number, etc.)
4. Name the field (e.g., "Repository Name")
5. Associate with appropriate screens and projects
6. Note the **field ID** (e.g., `customfield_10100`)

#### Update Code to Use Custom Fields:

```python
def update_jira_success_with_custom_fields(
    ticket_id: str,
    repo_data: Dict,
    correlation_id: str = None
) -> bool:
    """Enhanced version with custom fields."""

    try:
        client = JiraClient()

        # Add comment (existing functionality)
        comment_text = _build_success_comment(repo_data)
        client.client.add_comment(ticket_id, comment_text)

        # Get issue and update
        issue = client.client.issue(ticket_id)

        # Prepare updates
        current_labels = issue.fields.labels or []
        new_labels = list(set(current_labels + ["repository-created", "automated"]))

        # Update with custom fields
        # NOTE: Replace customfield_XXXXX with your actual field IDs
        update_fields = {
            "labels": new_labels,
            "customfield_10100": repo_data.get('name'),  # Repository Name
            "customfield_10101": repo_data.get('html_url'),  # Repository URL
            "customfield_10102": repo_data.get('id'),  # Repository ID
            "customfield_10103": repo_data.get('owner'),  # GitHub Org
            "customfield_10104": "Success",  # Creation Status
        }

        issue.update(fields=update_fields)

        log_and_monitor(
            "jira_custom_fields_updated",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id
        )

        return True

    except Exception as e:
        log_and_monitor(
            "jira_custom_fields_update_failed",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(e)
        )
        # Don't fail - custom fields are nice-to-have
        return False
```

---

### 🔍 **JQL Queries for Reporting**

#### **1. All Successful Repository Creations**

```sql
labels = "repository-created" AND labels = "automated"
```

#### **2. Successful Repos Created in Last 30 Days**

```sql
labels = "repository-created" AND created >= -30d
ORDER BY created DESC
```

#### **3. All Failed Attempts**

```sql
labels = "repository-creation-failed"
ORDER BY created DESC
```

#### **4. Failed Attempts Still Needing Attention**

```sql
labels = "repository-creation-failed" AND status != "Done" AND status != "Closed"
```

#### **5. Validation Failures (User Errors)**

```sql
labels = "repository-creation-failed" AND status = "Needs Information"
```

#### **6. Permission Failures (Platform Team Action Required)**

```sql
labels = "repository-creation-failed" AND assignee = "platform-team-bot" AND status = "Blocked"
```

#### **7. Repos Created by Specific User**

```sql
labels = "repository-created" AND reporter = "hiya.modi.here@gmail.com"
```

#### **8. Repos Created in Specific Organization**

```sql
labels = "repository-created" AND text ~ "Repo-Creation-Automation"
```

#### **9. Success Rate Analysis (Last 90 Days)**

```sql
# Total attempts
labels = "automated" AND created >= -90d

# Successful
labels = "repository-created" AND created >= -90d

# Failed
labels = "repository-creation-failed" AND created >= -90d
```

#### **10. Repos with Custom Field Filter (if using custom fields)**

```sql
"Repository Name" ~ "test-*" AND "Creation Status" = "Success"
```

---

### 📊 **JIRA Dashboard Widgets**

Create a JIRA dashboard with these widgets:

#### **Widget 1: Success Rate Pie Chart**
- **Filter:** `labels = "automated" AND created >= -30d`
- **Group by:** Labels (`repository-created` vs `repository-creation-failed`)
- **Chart Type:** Pie chart

#### **Widget 2: Creation Trend (Time Series)**
- **Filter:** `labels = "repository-created"`
- **Group by:** Created date
- **Chart Type:** Line chart
- **Time period:** Last 90 days

#### **Widget 3: Failed Tickets Needing Action**
- **Filter:** `labels = "repository-creation-failed" AND status != "Done"`
- **Chart Type:** Table/List
- **Columns:** Ticket, Summary, Assignee, Status, Created

#### **Widget 4: Top Requesters**
- **Filter:** `labels = "repository-created" AND created >= -30d`
- **Group by:** Reporter
- **Chart Type:** Bar chart

#### **Widget 5: Average Resolution Time**
- **Filter:** `labels = "automated" AND resolved >= -30d`
- **Chart Type:** Single stat
- **Metric:** Average time in status

---

### 📥 **Exporting Data from JIRA**

#### **Method 1: JIRA UI Export**

1. Run your JQL query
2. Click **Export** (top-right)
3. Choose format:
   - **Excel** (for spreadsheets)
   - **CSV** (for data analysis)
   - **JSON** (for programmatic access)

#### **Method 2: JIRA API Export (Programmatic)**

```python
from jira import JIRA
import csv

client = JIRA(
    server="https://your-domain.atlassian.net",
    basic_auth=("hiya.modi.here@gmail.com", "api_token")
)

# Get all successful repo creations
issues = client.search_issues(
    'labels = "repository-created"',
    maxResults=1000,
    fields='key,summary,created,reporter,labels,comment'
)

# Extract to CSV
with open('repositories.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        'Ticket ID',
        'Repository Name',
        'Repository URL',
        'Requester',
        'Created Date'
    ])

    for issue in issues:
        # Parse from comment (or use custom fields if implemented)
        comments = client.comments(issue.key)
        repo_name = None
        repo_url = None

        for comment in comments:
            if "Repository Created Successfully" in comment.body:
                # Extract data using regex
                import re
                name_match = re.search(r'\*Name:\* (.+)', comment.body)
                url_match = re.search(r'\*Web:\* \[(.+?)\|', comment.body)

                if name_match:
                    repo_name = name_match.group(1).strip()
                if url_match:
                    repo_url = url_match.group(1).strip()
                break

        writer.writerow([
            issue.key,
            repo_name or 'N/A',
            repo_url or 'N/A',
            issue.fields.reporter.displayName,
            issue.fields.created
        ])

print("Export complete: repositories.csv")
```

---

### 📈 **Sample Reports You Can Generate**

#### **Report 1: Monthly Success Rate**

```python
from jira import JIRA
from datetime import datetime, timedelta
from collections import defaultdict

client = JIRA(server=jira_url, basic_auth=(email, token))

# Get data for last 6 months
months = []
for i in range(6):
    month_start = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m-01')

    total = client.search_issues(
        f'labels = "automated" AND created >= "{month_start}" AND created < "{month_start}" + 30d',
        maxResults=0  # Just get count
    ).total

    success = client.search_issues(
        f'labels = "repository-created" AND created >= "{month_start}" AND created < "{month_start}" + 30d',
        maxResults=0
    ).total

    success_rate = (success / total * 100) if total > 0 else 0

    months.append({
        'month': month_start,
        'total': total,
        'success': success,
        'success_rate': success_rate
    })

for month in reversed(months):
    print(f"{month['month']}: {month['success']}/{month['total']} ({month['success_rate']:.1f}%)")
```

**Output:**
```
2025-10-01: 45/50 (90.0%)
2025-11-01: 52/55 (94.5%)
2025-12-01: 60/62 (96.8%)
2026-01-01: 58/60 (96.7%)
2026-02-01: 55/58 (94.8%)
2026-03-01: 48/50 (96.0%)
```

---

#### **Report 2: Failure Analysis by Type**

```python
# Get all failed tickets
failed_tickets = client.search_issues(
    'labels = "repository-creation-failed" AND created >= -90d',
    maxResults=1000
)

error_categories = defaultdict(int)

for ticket in failed_tickets:
    status = ticket.fields.status.name

    if status == "Needs Information":
        error_categories["Validation Errors"] += 1
    elif status == "Blocked" and ticket.fields.assignee.name == "platform-team-bot":
        error_categories["Permission Errors"] += 1
    else:
        error_categories["Other Errors"] += 1

print("\\nFailure Breakdown (Last 90 Days):")
for category, count in error_categories.items():
    print(f"  {category}: {count}")
```

**Output:**
```
Failure Breakdown (Last 90 Days):
  Validation Errors: 12
  Permission Errors: 3
  Other Errors: 2
```

---

## 🎯 **Advantages of Using JIRA as Source of Truth**

✅ **No Additional Infrastructure** - No database to manage
✅ **Built-in Audit Trail** - Every change is logged automatically
✅ **User-Friendly** - Stakeholders already use JIRA
✅ **Free** - No extra costs
✅ **Permissions** - Managed by JIRA (RBAC built-in)
✅ **Compliance** - JIRA audit logs meet compliance requirements
✅ **Searchable** - Powerful JQL for complex queries
✅ **Exportable** - CSV, Excel, JSON exports available
✅ **Dashboards** - Built-in visualization tools
✅ **Notifications** - Email/Slack notifications on ticket updates

---

## ⚠️ **Limitations to Be Aware Of**

❌ **Not Optimized for Analytics** - Large queries can be slow
❌ **JQL Limitations** - Complex aggregations are difficult
❌ **Data in Comments** - Requires parsing (unless using custom fields)
❌ **API Rate Limits** - 300 requests/minute for Cloud
❌ **No Real-Time Streaming** - Must poll API for updates

**Mitigation:** Use custom fields for structured data, cache query results, and limit query frequency.

---

## 📚 Additional Resources

### JIRA API Documentation
- [JIRA REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [JIRA Transitions API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-transitions-get)
- [JIRA Fields API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-fields/)
- [JQL Reference](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/)

---

## 🤝 Support

### Questions or Issues?

1. Review this document thoroughly
2. Check JIRA workflow configuration
3. Verify all environment variables are set correctly
4. Check logs with correlation ID for debugging
5. Contact platform team if infrastructure issues persist

---

**Document Version:** 1.0
**Last Updated:** 2026-03-30
**Status:** Ready for Implementation (awaiting JIRA access)
        # Categorize GitHub errors
        if e.status_code in [401, 403]:
            # PERMISSION/AUTH FAILURE
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "permission", str(e), correlation_id)

        elif e.status_code == 422 and "already exists" in str(e).lower():
            # BUSINESS RULE: Repository already exists
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)

        elif e.status_code in [408, 429, 500, 502, 503, 504]:
            # TRANSIENT FAILURE - will retry
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "transient", str(e), correlation_id)
            # Trigger retry mechanism here

        else:
            # UNKNOWN FAILURE - treat as business rule
            update_jira_failure(ticket_id, str(e), correlation_id)
            transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)

        raise

    except Exception as e:
        # UNKNOWN ERROR
        update_jira_failure(ticket_id, str(e), correlation_id)
        transition_ticket_on_failure(ticket_id, "business_rule", str(e), correlation_id)
        raise
```

---

## 📊 Error Categorization

### Decision Tree for Error Classification

```
Error Occurred
    │
    ├─→ ValidationError → "validation"
    │
    ├─→ GitHubAPIError
    │   │
    │   ├─→ status_code in [401, 403] → "permission"
    │   │
    │   ├─→ status_code == 422 AND "already exists" → "business_rule" (idempotent)
    │   │
    │   ├─→ status_code in [408, 429, 500, 502, 503, 504] → "transient"
    │   │
    │   └─→ Other status codes → "business_rule"
    │
    └─→ Other Exceptions → "business_rule"
```

### Error Type Mappings

| Error Type | HTTP Status Codes | Examples | Target Status | Assignee |
|------------|------------------|----------|---------------|----------|
| **validation** | N/A (pre-API) | Invalid repo name, missing fields | Needs Information | Reporter |
| **permission** | 401, 403 | Token expired, no org access | Blocked | Platform Team |
| **transient** | 408, 429, 500, 502, 503, 504 | Timeout, rate limit, server error | In Progress | (unchanged) |
| **business_rule** | 422, 409, others | Repo exists, quota exceeded | Blocked or Done | (unchanged) |

---

## 🧪 Testing Guide

### Prerequisites

1. ✅ JIRA access configured
2. ✅ Test JIRA project with appropriate workflow
3. ✅ Permissions to create/transition tickets

### Test Cases

#### Test 1: Success Transition

**Setup:**
1. Create a JIRA ticket manually (e.g., "TEST-001")
2. Set status to "In Progress"
3. Ensure "Done" transition is available

**Execute:**
```python
# Trigger repository creation with valid data
event = {
    "ticket_id": "TEST-001",
    "repo_name": "test-repo-success",
    "github_org": "Repo-Creation-Automation",
    # ... other valid fields
}
```

**Expected Result:**
- ✅ Repository created on GitHub
- ✅ JIRA comment added with success message
- ✅ Labels added: `repository-created`, `automated`
- ✅ **Ticket status changed to "Done"**
- ✅ Resolution set to "Done" (if configured)

---

#### Test 2: Validation Failure

**Setup:**
1. Create JIRA ticket "TEST-002"
2. Ensure "Needs Information" status exists

**Execute:**
```python
# Trigger with invalid repository name
event = {
    "ticket_id": "TEST-002",
    "repo_name": "Invalid_Name_With_Underscores",  # Should be kebab-case
    # ...
}
```

**Expected Result:**
- ✅ Repository NOT created
- ✅ JIRA comment with error details
- ✅ Label: `repository-creation-failed`
- ✅ **Status changed to "Needs Information"**
- ✅ **Assigned back to reporter**

---

#### Test 3: Permission Failure

**Setup:**
1. Use expired/invalid GitHub token
2. Create JIRA ticket "TEST-003"

**Execute:**
```python
# Use invalid token in environment
os.environ['GITHUB_TOKEN'] = 'invalid_token_xyz'
```

**Expected Result:**
- ✅ 403 error from GitHub
- ✅ JIRA comment with permission error
- ✅ **Status changed to "Blocked"**
- ✅ **Assigned to platform team**
- ✅ Label: `platform-team-action-required`

---

#### Test 4: Transient Failure Handling

**Setup:**
1. Simulate network timeout or rate limit

**Execute:**
```python
# Mock GitHub API to return 429 (rate limit)
```

**Expected Result:**
- ✅ JIRA comment about transient error
- ✅ **Status remains "In Progress"**
- ✅ Label: `auto-retry-scheduled`
- ✅ Retry mechanism triggered (if implemented)

---

#### Test 5: Repository Already Exists (Idempotent)

**Setup:**
1. Create repository manually first
2. Trigger automation with same name

**Execute:**
```python
# Attempt to create already-existing repo
```

**Expected Result:**
- ✅ Detection that repo exists
- ✅ JIRA comment with success (idempotent)
- ✅ **Status changed to "Done"**
- ✅ No error raised

---

### Manual Testing Checklist

- [ ] Verify all transitions exist in your JIRA workflow
- [ ] Test with `AUTO_TRANSITION_ON_SUCCESS=false` (should skip transitions)
- [ ] Test with non-existent target status name (should log warning)
- [ ] Verify assignee changes work correctly
- [ ] Check that labels are still added even if transition fails
- [ ] Confirm resolution is set only when required
- [ ] Test with workflow that doesn't require resolution
- [ ] Verify logging includes all correlation IDs

---

## 🔙 Rollback Plan

### If Issues Occur in Production

**Immediate Rollback:**
1. Set `AUTO_TRANSITION_ON_SUCCESS=false`
2. Set `AUTO_TRANSITION_ON_FAILURE=false`
3. Redeploy with these settings

**System will revert to:**
- ✅ Comments still added
- ✅ Labels still added
- ❌ No status transitions

**No data loss, fully backward compatible!**

---

## 📝 Implementation Checklist

### Phase 1: Configuration
- [ ] Add new environment variables to `.env`
- [ ] Update `src/config.py` with new settings
- [ ] Test configuration loading

### Phase 2: Success Transitions
- [ ] Implement `transition_ticket_on_success()`
- [ ] Update `update_jira_success()` to call new function
- [ ] Add comprehensive logging
- [ ] Test with real JIRA ticket

### Phase 3: Failure Handling
- [ ] Implement `transition_ticket_on_failure()`
- [ ] Implement `_handle_assignee_on_failure()`
- [ ] Update orchestrator with error categorization
- [ ] Test all failure scenarios

### Phase 4: Testing & Validation
- [ ] Run all test cases
- [ ] Verify workflow compatibility
- [ ] Check logs and monitoring
- [ ] Document any workflow-specific customizations

### Phase 5: Deployment
- [ ] Deploy to staging environment
- [ ] Monitor for 1-2 days
- [ ] Get user feedback
- [ ] Deploy to production
- [ ] Monitor closely for first week

---

## 🎯 Success Metrics

### After Implementation, Track:

1. **Automation Rate**
   - % of tickets auto-closed vs manually closed
   - Target: >90% auto-closed

2. **Accuracy**
   - % of tickets transitioned to correct status
   - Target: >95% accuracy

3. **Error Routing**
   - % of validation errors correctly sent back to reporter
   - % of permission errors correctly sent to platform team
   - Target: 100% correct routing

4. **Cycle Time**
   - Average time from "In Progress" to "Done"
   - Should decrease with automation

5. **Manual Intervention**
   - Number of tickets requiring manual status changes
   - Target: <5% need manual intervention

---

## 📚 Additional Resources

### JIRA API Documentation
- [JIRA Transitions API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-transitions-get)
- [JIRA Fields API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-fields/)

### Useful JIRA Queries (JQL)
```sql
-- All automated success tickets
labels = "repository-created" AND labels = "automated"

-- All failures needing attention
labels = "repository-creation-failed" AND status != "Done"

-- All tickets blocked on platform team
assignee = platform-team-bot AND status = "Blocked"
```

---

## 🤝 Support

### Questions or Issues?

1. Review this document thoroughly
2. Check JIRA workflow configuration
3. Verify all environment variables are set correctly
4. Check logs with correlation ID for debugging
5. Contact platform team if infrastructure issues persist

---

**Document Version:** 1.0
**Last Updated:** 2026-03-30
**Status:** Ready for Implementation (awaiting JIRA access)

