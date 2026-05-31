# GitHub Auto-Repository Provisioning System

> **Event-driven serverless system that automates GitHub repository creation from JIRA ticket workflows, eliminating manual DevOps toil for engineering teams.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Terraform](https://img.shields.io/badge/terraform-%3E%3D1.0-blueviolet.svg)](https://www.terraform.io/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🏗️ Architecture

```
                    ┌────────────────┐
                    │   JIRA Ticket  │
                    │  (Form Submit) │
                    └───────┬────────┘
                            │ Webhook (HTTPS)
                            ▼
                    ┌────────────────┐
                    │  Lambda 1:     │
                    │  Webhook       │─────────────────────────┐
                    │  Handler       │                         │
                    └───────┬────────┘                         │
                            │ SQS Message                     │ Validation
                            ▼                                  │ Failure
                    ┌────────────────┐                         │
                    │   SQS Queue    │                         │
                    │  (Main Queue)  │                         │
                    └───────┬────────┘                         │
                            │ Event Source Mapping             │
                            ▼                                  │
                    ┌────────────────┐                         │
                    │  Lambda 2:     │    ┌────────────────┐   │
                    │  Repo Creator  │───►│  GitHub API    │   │
                    │  (Core Logic)  │    │  (App Auth)    │   │
                    └──┬──────────┬──┘    └────────────────┘   │
                       │          │                             │
              Success  │          │ 3x Retry Failure           │
                       ▼          ▼                            │
              ┌──────────┐  ┌──────────┐                      │
              │  JIRA    │  │  Dead    │                      │
              │  Update  │  │  Letter  │                      │
              │  ✅ Done │  │  Queue   │                      │
              └──────────┘  └────┬─────┘                      │
                                 │                             │
                                 ▼                             │
                         ┌────────────────┐                   │
                         │  Lambda 3:     │◄──────────────────┘
                         │  DLQ Handler   │
                         │  (Escalation)  │
                         └───────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  JIRA    │ │  Slack   │ │CloudWatch│
              │  Comment │ │  Alert   │ │  Metrics │
              └──────────┘ └──────────┘ └──────────┘
```

**27 AWS resources** deployed via modular Terraform across 5 reusable infrastructure modules.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Event-Driven Architecture** | SQS → Lambda pipeline with automatic retry and dead-letter queue escalation |
| **Idempotent Design** | Repository existence check before creation — safe to retry without duplicates |
| **Smart Error Classification** | Transient errors (5xx, 429) trigger retry; permanent errors (4xx) fail immediately |
| **GitHub App Authentication** | JWT-based auth with dynamic multi-organization installation ID discovery |
| **Automatic JIRA Updates** | Success/failure comments, label management, and ticket state transitions |
| **Production Observability** | CloudWatch custom metrics, structured JSON logging, and Slack alerting |
| **Infrastructure as Code** | Modular Terraform with environment-based promotion (dev → staging → prod) |
| **Custom Exception Hierarchy** | Typed error handling with retryability classification and JSON serialization |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11 |
| **Compute** | AWS Lambda (×3 functions) |
| **Messaging** | Amazon SQS (main queue + DLQ) |
| **Secrets** | AWS Secrets Manager |
| **Monitoring** | Amazon CloudWatch (metrics + logs) |
| **Alerts** | Amazon SNS + Slack Webhooks |
| **IaC** | Terraform (5 reusable modules) |
| **Auth** | GitHub App (JWT + Installation Access Tokens) |
| **Validation** | Pydantic v2 (models + settings) |
| **Logging** | structlog (JSON structured logging) |
| **APIs** | GitHub REST API v2022-11-28, JIRA REST API |

---

## 📁 Project Structure

```
├── src/                          # Application source code
│   ├── config.py                 # Pydantic-based configuration management
│   ├── handlers/                 # Lambda entry points
│   │   ├── github_handler.py     # Main repo creation handler (Lambda 2)
│   │   └── dlq_handler.py        # Dead letter queue handler (Lambda 3)
│   ├── business/                 # Core business logic
│   │   ├── workflow_processor.py # Orchestrates the creation workflow
│   │   ├── validators.py         # Pydantic input validation (kebab-case, etc.)
│   │   └── message_parser.py     # SQS message parsing + sanitization
│   ├── integrations/             # External service adapters
│   │   ├── github/               # GitHub App auth + repo creation
│   │   ├── jira/                 # JIRA API client + ticket updates
│   │   ├── aws/                  # AWS Secrets Manager integration
│   │   └── messaging/            # Slack notification system
│   ├── observability/            # Logging, metrics, and monitoring
│   │   ├── cloudwatch_metrics.py # CloudWatch custom metrics emission
│   │   ├── logging_core.py       # Structured JSON logging (structlog)
│   │   └── metrics_collector.py  # In-memory metrics aggregation
│   └── shared/                   # Cross-cutting concerns
│       ├── exceptions.py         # Custom exception hierarchy
│       └── error_formatting.py   # Error categorization + JIRA formatting
├── infra/                        # Terraform infrastructure
│   ├── modules/                  # Reusable Terraform modules
│   │   ├── repo-creator/         # SQS queues + Lambda function
│   │   ├── dlq-handler/          # DLQ Lambda function
│   │   ├── lambda-layer/         # Python dependencies layer
│   │   ├── secrets/              # AWS Secrets Manager
│   │   └── notifications/        # SNS alert topics
│   └── environment/              # Environment-specific configs
│       └── test/                 # Test environment deployment
├── tests/                        # Test suites
│   ├── test_jira_client.py       # JIRA client unit tests (pytest)
│   ├── test_check_repository_exists.py
│   ├── test_create_repository_cases.py
│   └── test_client_manager_caching.py
├── docs/                         # Documentation (21 docs)
├── .github/workflows/            # CI/CD pipeline
└── requirements.txt              # Python dependencies
```

---

## 🔄 How It Works

### Happy Path
1. **Engineer creates a JIRA ticket** with repository details (name, org, type, ownership)
2. **JIRA Automation triggers webhook** → hits Lambda Function URL
3. **Webhook Handler** validates payload and sends to SQS queue
4. **Repo Creator Lambda** is triggered:
   - Validates input (kebab-case repo name, required fields)
   - Checks if repository already exists (idempotency)
   - Creates repository via GitHub API with custom properties
   - Updates JIRA ticket with success comment + transitions to "Done"
5. **Engineer gets notification** — repository URL in JIRA comment

### Failure Path
1. **Transient errors** (GitHub 5xx, rate limits) → automatic SQS retry (3 attempts)
2. **After 3 failures** → message moves to Dead Letter Queue
3. **DLQ Handler Lambda** → updates JIRA with failure details + sends Slack alert
4. **Permanent errors** (validation, 4xx) → immediate JIRA update, no retry

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured with admin permissions
- Terraform ≥ 1.0
- GitHub App credentials ([setup guide](docs/CREDENTIALS_SETUP.md))
- JIRA API token ([setup guide](docs/CREDENTIALS_SETUP.md))

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your GitHub App and JIRA credentials
```

### 3. Deploy Infrastructure
```bash
cd infra/environment/test
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with credentials
terraform init
terraform apply
```

### 4. Run Tests
```bash
pytest tests/ -v --cov=src
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Cold Start | ~1,650ms |
| Avg Execution | ~546ms |
| Memory Usage | 134 MB / 512 MB |
| Success Rate | >95% target |
| End-to-End Latency | 10–30 seconds |

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html

# Quick validator tests
python -m pytest tests/test_jira_client.py -v
```

---

## 🔐 Security

- ✅ All secrets stored in AWS Secrets Manager (encrypted at rest + in transit)
- ✅ IAM roles follow least-privilege principle
- ✅ GitHub App authentication (no long-lived PATs)
- ✅ No credentials in code or environment variables
- ✅ Sensitive data masked in structured logs

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE_FINAL.md) | Complete system architecture and execution flow |
| [AWS Setup Guide](docs/AWS_SERVERLESS_SETUP_GUIDE.md) | Step-by-step AWS deployment guide |
| [Credentials Setup](docs/CREDENTIALS_SETUP.md) | GitHub App and JIRA credential configuration |
| [Notification Guide](docs/NOTIFICATION_INTEGRATION_GUIDE.md) | Slack and SNS alert setup |
| [Infrastructure README](infra/README.md) | Terraform modules and deployment details |

---

## 🗺️ Roadmap

- [ ] Branch protection rule automation
- [ ] Repository template provisioning (README, .gitignore, CI workflows)
- [ ] Team-based access control assignment
- [ ] Security scanning setup (Dependabot, CodeQL)
- [ ] Multi-cloud support (Azure Functions, GCP Cloud Run)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
