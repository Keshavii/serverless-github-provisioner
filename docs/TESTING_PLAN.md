# 🧪 Complete Testing Plan - GitHub Repository Automation

Comprehensive testing strategy to validate the entire system before production deployment.

---

## 📋 Testing Levels

| Level | What | Tools | Duration | When |
|-------|------|-------|----------|------|
| **1. Unit Tests** | Individual functions | pytest, mocks | 2-5 min | Every commit |
| **2. Integration Tests** | Component interactions | pytest, real APIs | 10-15 min | Before deployment |
| **3. E2E Tests** | Full workflow | Manual/automated | 20-30 min | Before release |
| **4. Load Tests** | Performance | Locust, SQS | 30+ min | Before production |

---

## 🎯 What to Test

### **Already Implemented ✅**
- ✅ Unit tests for JIRA client (`tests/test_jira_client.py`)
- ✅ GitHub client existence checks (`tests/test_check_repository_exists.py`)
- ✅ Repository creation tests (`tests/test_create_repository_cases.py`)
- ✅ Client caching tests (`tests/test_client_manager_caching.py`)
- ✅ Test runner script (`run_jira_tests.sh`)
- ✅ E2E test script (`test_e2e_complete.py`)
- ✅ Webhook failure tests (`test_webhook_failure.py`)

### **Missing Tests ⚠️**
- ⚠️ Notification system tests (new)
- ⚠️ DLQ handler tests
- ⚠️ Webhook handler tests
- ⚠️ SQS integration tests
- ⚠️ Lambda deployment tests
- ⚠️ Infrastructure validation tests

---

## 🚀 Quick Start Testing

### **1. Run All Unit Tests (2 min)**
```bash
# Activate environment
source venv/bin/activate

# Run all unit tests
pytest tests/ -v --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

### **2. Run JIRA Integration Tests (5 min)**
```bash
# Requires real JIRA credentials
./run_jira_tests.sh <TICKET_ID>

# Example
./run_jira_tests.sh REPO-123
```

### **3. Run GitHub Tests (5 min)**
```bash
# Test repository existence check
python tests/test_check_repository_exists.py

# Test repository creation
python tests/test_create_repository_cases.py

# Test client caching
python tests/test_client_manager_caching.py
```

### **4. Run E2E Test (10 min)**
```bash
# Full workflow test
python test_e2e_complete.py
```

---

## 📝 Detailed Testing Checklist

### **Phase 1: Local Development Testing** (30 min)

#### ✅ **1.1 Unit Tests**
```bash
# All unit tests
pytest tests/ -v

# Specific module
pytest tests/test_jira_client.py -v
pytest tests/test_create_repository_cases.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

**Expected:** All tests pass, >80% coverage

#### ✅ **1.2 Code Quality**
```bash
# Type checking (if using mypy)
mypy src/

# Linting
pylint src/
flake8 src/

# Security scan
bandit -r src/
```

---

### **Phase 2: AWS Infrastructure Testing** (45 min)

#### ✅ **2.1 Terraform Validation**
```bash
cd infra/enviroment/test

# Validate syntax
terraform validate

# Check plan
terraform plan

# Estimate costs
terraform cost-estimate  # if using Infracost
```

#### ✅ **2.2 Lambda Deployment**
```bash
# Deploy infrastructure
terraform apply

# Verify Lambda functions exist
aws lambda list-functions --query 'Functions[?contains(FunctionName, `github-repo-automation`)]'

# Check Lambda logs
aws logs tail /aws/lambda/github-repo-automation-test-repo-creator --follow
```

#### ✅ **2.3 SQS Queues**
```bash
# Check queues exist
aws sqs list-queues | grep github-repo-automation

# Send test message
aws sqs send-message \
  --queue-url $(terraform output -raw sqs_queues | jq -r '.main_queue_url') \
  --message-body file://test-payload.json
```

---

### **Phase 3: Integration Testing** (60 min)

