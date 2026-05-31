# JIRA Ticket Required Fields

## Overview

This document lists all the mandatory fields that must be filled in the JIRA Change Request (CR) ticket to trigger the automated GitHub repository creation process.

---

## 📋 Mandatory JIRA Ticket Fields

### **Section A: Repository Details**

| Field Name | Field Key | Type | Validation Rules | Example |
|------------|-----------|------|------------------|---------|
| **Repo Name** | `repo_name` | String | - Must be kebab-case<br>- No spaces<br>- Lowercase letters, numbers, hyphens only<br>- Cannot start/end with hyphen | `my-awesome-service` |
| **GitHub Organization** | `github_org` | String | - Must be valid GitHub org name<br>- Organization must exist<br>- Not empty | `hiyamodi-corp` |
| **Description/Purpose** | `description` | String | - Brief description of repository purpose<br>- Not empty<br>- Recommended: 50-200 characters | `Service for handling user authentication` |

---

### **Section B: Ownership Details**

| Field Name | Field Key | Type | Validation Rules | Example |
|------------|-----------|------|------------------|---------|
| **VP Name** | `vp_name` | String | - Full name of VP<br>- Not empty | `John Smith` |
| **Director Name** | `director_name` | String | - Full name of Director<br>- Not empty | `Jane Doe` |
| **Engineering Manager Name** | `em_name` | String | - Full name of Engineering Manager<br>- Not empty | `Bob Johnson` |
| **Documentation Link** | `documentation_link` | URL | - Must be valid URL format<br>- Should point to Confluence/SharePoint/Runbook<br>- Must be accessible | `https://hiyamodi.com/display/TEAM/service-docs` |
| **Product Line** | `product_line` | String | - Product line this repo belongs to<br>- Not empty | `Customer Platform` |
| **Department** | `department` | String | - Department owning the repository<br>- Not empty | `Engineering` |

---

### **Section C: Repository Classification**

| Field Name | Field Key | Type | Validation Rules | Example |
|------------|-----------|------|------------------|---------|
| **Repository Type** | `repo_type` | Enum | - Must be one of:<br>  - `Internal`<br>  - `Private` | `Internal` |
| **Code Type** | `code_type` | Enum | - Must be one of:<br>  - `Java`<br>  - `Nodejs`<br>  - `Go`<br>  - `Python`<br>  - `terraform`<br>  - `helm` | `Java` |

---

## 📝 JIRA Ticket Template

### **Change Request Title Format:**
```
GitHub Repository Creation – <repo-name>
```

### **Ticket Description Template:**

```
1) Repository Details
- Repo Name: <repo-name>
- GitHub Org: <org-name>
- Description/Purpose: <brief description>

2) Ownership Details
- VP Name: <vp-name>
- Director Name: <director-name>
- EM Name: <em-name>
- Documentation Link: <confluence/sharepoint/runbook-link>
- Product Line: <product-line>
- Department: <department>

3) Classification
- Repo Type: Internal / Private
- Code Type: Java / Nodejs / Go / Python / terraform / helm
```

---

## ✅ Validation Rules Summary

### **Repo Name Validation:**
- ✅ Valid: `my-service`, `user-auth-api`, `payment-gateway-v2`
- ❌ Invalid: `MyService`, `user_auth`, `my service`, `-my-service`, `my-service-`

### **Repository Type:**
- ✅ `Internal` - Visible to all members of the GitHub organization
- ✅ `Private` - Visible only to repository collaborators

### **Code Type:**
- Determines the `.gitignore` template to use (if implemented)
- Used in README generation
- Helps with repository classification

---

## 🔄 Workflow Trigger

**The automated process triggers when:**
1. ✅ JIRA ticket is created with all mandatory fields
2. ✅ RELB approves the change request
3. ✅ Ticket status is changed to **"In Progress"**
4. ✅ JIRA webhook fires and sends payload to the automation system

---

## 📊 Field Mapping to Functions

| JIRA Field | Used By Function | Purpose |
|------------|------------------|---------|
| `repo_name` | Input Validation, Existence Check, Repo Creation | Repository identifier |
| `github_org` | Input Validation, Existence Check, Repo Creation | Organization context |
| `description` | Input Validation, Repo Creation | Repository description |
| `vp_name` | Input Validation, README Generation | Ownership tracking |
| `director_name` | Input Validation, README Generation | Ownership tracking |
| `em_name` | Input Validation, README Generation | Ownership tracking |
| `documentation_link` | Input Validation, README Generation | Reference documentation |
| `product_line` | Input Validation, README Generation | Product classification |
| `department` | Input Validation, README Generation | Organizational classification |
| `repo_type` | Input Validation, Repo Creation | Visibility setting |
| `code_type` | Input Validation, README Generation | Technology classification |

---

## ⚠️ Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid repo name format` | Repo name not in kebab-case or contains invalid characters | Use lowercase letters, numbers, and hyphens only. Example: `my-service-name` |
| `Missing required field` | One or more mandatory fields are empty | Fill in all fields in sections A, B, and C |
| `Invalid URL format` | Documentation link is not a valid URL | Provide full URL: `https://...` |
| `Invalid repo type` | Repo type not in allowed values | Use either `Internal` or `Private` |
| `Invalid code type` | Code type not in allowed values | Use one of: `Java`, `Nodejs`, `Go`, `Python`, `terraform`, `helm` |

---

## 📌 Notes

1. **All fields are mandatory** - Missing any field will cause validation failure
2. **Case-sensitive values** - Use exact case as specified (e.g., `Nodejs` not `NodeJS`)
3. **Ownership chain** - VP → Director → EM must be complete and accurate
4. **Documentation link** - Must be accessible to the platform team for verification
5. **Repo name uniqueness** - System checks if repo already exists (idempotent design)

---

## 🔗 Related Documents

- [REQUIREMENTS.md](./REQUIREMENTS.md) - Functional and non-functional requirements
- [ARCHITECTURE_FINAL.md](./ARCHITECTURE_FINAL.md) - Final architecture and flow diagram
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Primary AWS architecture (Lambda Function URL)
- [ARCHITECTURE_SECONDARY.md](./ARCHITECTURE_SECONDARY.md) - Secondary architecture (API Gateway)

