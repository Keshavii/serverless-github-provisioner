# 🧪 JIRA Client Testing Guide

Complete guide for testing the JIRA client functionality with both unit tests and integration tests.

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Test Coverage](#test-coverage)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 **Overview**

The JIRA client has two types of tests:

| Test Type | Purpose | Uses Real JIRA | Speed | When to Run |
|-----------|---------|----------------|-------|-------------|
| **Unit Tests** | Test logic with mocks | ❌ No | ⚡ Fast | Always (CI/CD) |
| **Integration Tests** | Test with real JIRA | ✅ Yes | 🐢 Slow | Before deployment |

---

## 🔬 **Unit Tests**

### **What's Tested**

Unit tests in `tests/test_jira_client.py` cover:

✅ **JiraClient Initialization**
- Initialization with default credentials
- Initialization with custom credentials
- Authentication failure handling

✅ **Comment Building**
- Success comment formatting
- Failure comment formatting
- JIRA markup syntax

✅ **update_jira_success Function**
- Adding comments to tickets
- Updating ticket labels
- Error handling (403, 404, network errors)
- Label update failure (best-effort)

✅ **update_jira_failure Function**
- Adding failure comments
- Updating failure labels
- Best-effort error handling

✅ **transition_ticket_on_success Function**
- Transitioning tickets when enabled
- Skipping when disabled
- Handling missing transitions
- Including resolution fields
- Best-effort error handling

✅ **Error Handling**
- 401 authentication errors
- 403 permission errors
- 404 not found errors
- Network timeouts
- Generic exceptions

### **Running Unit Tests**

#### **Option 1: Using Test Runner Script (Recommended)**

```bash
./run_jira_tests.sh
```

#### **Option 2: Using pytest Directly**

```bash
# Activate virtual environment
source venv/bin/activate

# Run all JIRA client tests
pytest tests/test_jira_client.py -v

# Run specific test class
pytest tests/test_jira_client.py::TestUpdateJiraSuccess -v

# Run specific test
pytest tests/test_jira_client.py::TestUpdateJiraSuccess::test_success_update_adds_comment_and_labels -v

# Run with coverage report
pytest tests/test_jira_client.py --cov=src.jira_client --cov-report=html
```

### **Expected Output**

```
tests/test_jira_client.py::TestJiraClientInitialization::test_init_with_default_credentials PASSED
tests/test_jira_client.py::TestJiraClientInitialization::test_init_with_custom_credentials PASSED
tests/test_jira_client.py::TestCommentBuilding::test_build_success_comment PASSED
tests/test_jira_client.py::TestCommentBuilding::test_build_failure_comment PASSED
...
======================== 20 passed in 2.5s ========================
```

---

## 🌐 **Integration Tests**

### **What's Tested**

Integration tests in `test_jira_integration.py` test with a **real JIRA ticket**:

✅ **Test 1: JIRA Connection**
- Authenticates with JIRA
- Retrieves user information

✅ **Test 2: Get Ticket Information**
- Retrieves ticket details
- Displays summary, status, type

✅ **Test 3: Comment Formatting**
- Generates success/failure comments
- Previews formatted output

✅ **Test 4: Add Comment** (Optional)
- Adds test comment to ticket
- Verifies comment appears in JIRA

✅ **Test 5: Get Transitions**
- Lists available transitions
- Shows transition IDs

✅ **Test 6: Update Labels** (Optional)
- Adds test label to ticket
- Verifies label update

### **Prerequisites**

1. **Valid JIRA credentials** in `.env`:
   ```bash
   JIRA_URL=https://your-hiyamodi.atlassian.net
   JIRA_EMAIL=hiya.modi.here@gmail.com
   JIRA_API_TOKEN=your_api_token
   ```

2. **JIRA ticket** that you have access to:
   - Must exist in your JIRA instance
   - You must have permission to view and comment
   - Example: `ENG-12345`, `PM-789`, etc.

### **Running Integration Tests**

#### **Option 1: Using Test Runner Script (Recommended)**

```bash
./run_jira_tests.sh <TICKET_ID>
```

**Example:**
```bash
./run_jira_tests.sh ENG-12345
```

This will:
1. Run unit tests first
2. If unit tests pass, run integration tests with the ticket

#### **Option 2: Direct Python Script**

```bash
python test_jira_integration.py <TICKET_ID>
```

**Example:**
```bash
python test_jira_integration.py ENG-12345
```

### **Interactive Prompts**

The integration test will ask for confirmation before making changes:

```
⚠️ Do you want to add a test comment to ENG-12345? (y/N):
```

- Type `y` to proceed with the test
- Type `N` (or press Enter) to skip the test

**Note:** Tests that modify the ticket (comment, labels) are optional and require confirmation.

### **Expected Output**

```
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪
  JIRA CLIENT INTEGRATION TESTS
  Ticket: ENG-12345
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪

================================================================================
  TEST 1: JIRA Connection
================================================================================

✅ Successfully connected to JIRA!
   User: Hiya Modi
   Email: hiya.modi.here@gmail.com
   Account ID: 712020:abc123...

================================================================================
  TEST 2: Get Ticket Information - ENG-12345
================================================================================

✅ Successfully retrieved ticket: ENG-12345
   Summary: Create new GitHub repository
   Status: In Progress
   Type: Story
   Created: 2024-01-15T10:30:00.000+0000
   Reporter: Hiya Modi

...

================================================================================
  TEST SUMMARY
================================================================================

✅ PASSED - connection
✅ PASSED - ticket_info
✅ PASSED - formatting
✅ PASSED - add_comment
✅ PASSED - transitions
✅ PASSED - labels

Results: 6/6 tests passed
```

---

## 📊 **Test Coverage**

### **Viewing Coverage Report**

Generate an HTML coverage report:

```bash
pytest tests/test_jira_client.py --cov=src.jira_client --cov-report=html
```

Open the report:

```bash
open htmlcov/index.html
```

### **Current Coverage**

The unit tests aim for **>90% code coverage** of `jira_client.py`:

| Module | Statements | Missing | Coverage |
|--------|-----------|---------|----------|
| `src/jira_client.py` | ~150 | <15 | >90% |

---

## 🛠️ **Troubleshooting**

### **Issue: Import Errors**

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Make sure you're in the project root
cd github-repo-auto/Github-Auto-Repo-Creation

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### **Issue: JIRA Authentication Failed**

**Error:**
```
❌ JIRA connection failed: Failed to authenticate with JIRA
```

**Solution:**

1. Check `.env` file exists and contains:
   ```bash
   JIRA_URL=https://your-hiyamodi.atlassian.net
   JIRA_EMAIL=hiya.modi.here@gmail.com
   JIRA_API_TOKEN=your_api_token
   ```

2. Verify credentials:
   ```bash
   curl -u hiya.modi.here@gmail.com:your-api-token \
     https://your-hiyamodi.atlassian.net/rest/api/2/myself
   ```

3. Generate new API token:
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Create new token
   - Update `.env` file

---

### **Issue: Ticket Not Found**

**Error:**
```
❌ Cannot access ticket ENG-12345
```

**Solution:**

1. Verify ticket ID is correct
2. Check ticket exists in JIRA
3. Verify you have permission to view the ticket
4. Try accessing ticket in browser first

---

### **Issue: Permission Denied**

**Error:**
```
❌ JIRA permission denied during update ticket
```

**Solution:**

1. Check your JIRA user has permission to:
   - Add comments to tickets
   - Edit tickets (for labels)
   - Transition tickets (for status changes)

2. Ask JIRA admin to grant permissions

---

### **Issue: Tests Fail with Real JIRA**

**Symptom:** Unit tests pass but integration tests fail

**Solution:**

1. This is expected if:
   - JIRA credentials are invalid
   - JIRA is down
   - Network issues

2. Unit tests use mocks and don't need real JIRA
3. Integration tests require working JIRA connection

4. To run only unit tests:
   ```bash
   ./run_jira_tests.sh
   # (without ticket ID)
   ```

---

## 📝 **Test Files Overview**

| File | Purpose | Type |
|------|---------|------|
| `tests/test_jira_client.py` | Unit tests with mocks | Unit |
| `test_jira_integration.py` | Integration tests with real JIRA | Integration |
| `run_jira_tests.sh` | Test runner script | Script |

---

## 🚀 **Quick Reference**

### **Run Only Unit Tests**
```bash
./run_jira_tests.sh
```

### **Run Unit + Integration Tests**
```bash
./run_jira_tests.sh <TICKET_ID>
```

### **Run Specific Test**
```bash
pytest tests/test_jira_client.py::TestUpdateJiraSuccess -v
```

### **Run with Coverage**
```bash
pytest tests/test_jira_client.py --cov=src.jira_client --cov-report=html
```

### **Run Integration Test Only**
```bash
python test_jira_integration.py <TICKET_ID>
```

---

## 🎯 **Best Practices**

1. ✅ **Always run unit tests** before committing code
2. ✅ **Run integration tests** before deploying to production
3. ✅ **Use a test JIRA ticket** for integration tests (not production tickets)
4. ✅ **Check coverage** to ensure all code paths are tested
5. ✅ **Update tests** when adding new functionality
6. ✅ **Document test changes** in commit messages

---

## 📚 **Additional Resources**

- [PyTest Documentation](https://docs.pytest.org/)
- [JIRA Python Library](https://jira.readthedocs.io/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)
- [Test Coverage](https://coverage.readthedocs.io/)

---

**Happy Testing! 🧪✨**

