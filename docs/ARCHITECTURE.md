# GitHub Repository Automation - System Architecture (Primary)

## 📋 Document Information

- **Architecture Type:** Event-Driven Serverless
- **Version:** 1.0 (Primary - Lambda Function URL)
- **Last Updated:** March 27, 2026
- **Status:** Recommended Architecture

---

## 🎯 Overview

This document describes the **primary recommended architecture** for the GitHub Repository Automation system using **AWS Lambda Function URL** for JIRA webhook integration.

### Why This Architecture?

**✅ Simpler:** No API Gateway needed - Lambda Function URL provides the HTTP endpoint  
**✅ Cost-Effective:** Eliminates API Gateway costs (~$3.50 per million requests)  
**✅ Serverless:** Fully managed, auto-scaling, pay-per-use  
**✅ Event-Driven:** Triggered by JIRA webhook events  
**✅ Reliable:** SQS + DLQ ensures no message loss  

### Alternative Architecture

> **Note:** For an alternative architecture using **API Gateway** instead of Lambda Function URL, see [ARCHITECTURE_SECONDARY.md](./ARCHITECTURE_SECONDARY.md)

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
                   (HTTPS POST to Lambda URL)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              LAMBDA FUNCTION URL (Webhook Receiver)                  │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Function: jira-webhook-receiver                               │ │
│  │  Runtime: Python 3.11                                          │ │
│  │  Memory: 256 MB                                                │ │
│  │  Timeout: 30 seconds                                           │ │
│  │                                                                 │ │
│  │  Operations:                                                   │ │
│  │  1. Receive JIRA webhook POST request                          │ │
│  │  2. Validate webhook signature (optional)                      │ │
│  │  3. Filter events (only "In Progress" status)                  │ │
│  │  4. Extract ticket custom fields                               │ │
│  │  5. Send message to SQS queue                                  │ │
│  │  6. Return HTTP 200 to JIRA                                    │ │
│  │                                                                 │ │
│  │  Duration: ~200ms                                              │ │
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
│  │  2. Validate required fields (Pydantic)                        │ │
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




> For alternative architecture using API Gateway, see [ARCHITECTURE_SECONDARY.md](./ARCHITECTURE_SECONDARY.md)

