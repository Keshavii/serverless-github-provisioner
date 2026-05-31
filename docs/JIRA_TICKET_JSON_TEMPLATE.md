# JIRA Ticket JSON Template

## Overview

**⚠️ IMPORTANT: The automation now accepts ONLY JSON format.**

Copy the JSON template below into your JIRA ticket description field to trigger automated GitHub repository creation.

---

## 📋 **JSON Template**

### **Complete Template (Copy this into your JIRA ticket description)**

```json
{
  "repository_details": {
    "repo_name": "arc-core-photon-data-diff-service",
    "github_org": "hiyamodi-foundation",
    "repo_type": "Private",
    "description": "To create data diff service using duckdb",
    "code_type": "Java"
  },
  "ownership_details": {
    "vp_name": "Shankar Umamaheshwaran",
    "director_name": "Surya Narayanan",
    "em_name": "Allwin S",
    "product_line": "ARC",
    "department": "Core (Application Platform)"
  },
  "optional_metadata": {
    "documentation_link": "https://hiyamodi.com/display/ARC/photon-data-diff",
    "bucket_name": "arc-core-photon-data-diff-service",
    "additional_notes": "",
    "tags": [],
    "cost_center": "",
    "project_id": ""
  }
}
```

**💡 Tip:** You can also use the template file at `JIRA_TICKET_TEMPLATE.json` in the project root.

---

## ✅ **Mandatory Fields**

### **repository_details** (Required)
- `repo_name` - Repository name in kebab-case (e.g., `my-service-name`)
- `github_org` - GitHub organization (e.g., `hiyamodi-foundation`)
- `repo_type` - One of: `Internal` or `Private`
- `description` - Repository description/purpose (10-500 characters)
- `code_type` - One of: `Java`, `Nodejs`, `Go`, `Python`, `terraform`, `helm`

### **ownership_details** (Required)
- `vp_name` - VP full name
- `director_name` - Director full name
- `em_name` - Engineering Manager full name
- `product_line` - Product line name
- `department` - Department name

---

## 📝 **Optional Fields**

### **optional_metadata** (Optional)
- `documentation_link` - Documentation link (Confluence/SharePoint/Runbook)
- `bucket_name` - AWS S3 bucket name (if applicable)
- `additional_notes` - Any additional context
- `tags` - Array of custom tags
- `cost_center` - Cost center code
- `project_id` - Project tracking ID

**All fields in `optional_metadata` are non-mandatory and will not cause validation errors if missing.**

---

## 📖 **Example Tickets**

### **Example 1: Full Template (with documentation and bucket name)**
```json
{
  "repository_details": {
    "repo_name": "arc-core-photon-data-diff-service",
    "github_org": "hiyamodi-foundation",
    "repo_type": "Private",
    "description": "To create data diff service using duckdb",
    "code_type": "Java"
  },
  "ownership_details": {
    "vp_name": "Shankar Umamaheshwaran",
    "director_name": "Surya Narayanan",
    "em_name": "Allwin S",
    "product_line": "ARC",
    "department": "Core (Application Platform)"
  },
  "optional_metadata": {
    "documentation_link": "https://hiyamodi.com/display/ARC/photon-data-diff",
    "bucket_name": "arc-core-photon-data-diff-service"
  }
}
```

### **Example 2: Minimal Template (without optional fields)**
```json
{
  "repository_details": {
    "repo_name": "test-automation-repo-007",
    "github_org": "Repo-Creation-Automation",
    "repo_type": "Private",
    "description": "Test repository for automation system",
    "code_type": "Python"
  },
  "ownership_details": {
    "vp_name": "Hiya Modi",
    "director_name": "Hiya Modi",
    "em_name": "Bob Johnson",
    "product_line": "Test Product",
    "department": "Engineering"
  }
}
```

---

## 🔧 **How to Use**

1. **Copy the JSON template** above
2. **Fill in your values** (replace example values)
3. **Paste into JIRA ticket description field**
4. **Submit the ticket**
5. **Wait for automation** to create the repository

---

## ⚠️ **Important Notes**

1. **Valid JSON Required** - The description must be valid JSON format
2. **Case Sensitive** - Field values like `Private`, `Java`, `Nodejs` are case-sensitive
3. **Documentation Link is Optional** - You can include it in `optional_metadata` or omit it entirely
4. **Optional Fields** - You can omit the entire `optional_metadata` section if not needed

---

## 🆚 **JSON vs Text Format**

### **❌ Old Text Format** (Still supported for backward compatibility)
```
Repository Creation Request

Repository Details:
- Repository Name: test-automation-repo-007
- GitHub Organization: Repo-Creation-Automation
...
```

### **✅ New JSON Format** (Recommended)
```json
{
  "repository_details": {
    "repo_name": "test-automation-repo-007",
    ...
  }
}
```

**Benefits of JSON:**
- ✅ Easier to parse (no regex needed)
- ✅ Supports optional fields cleanly
- ✅ Better validation
- ✅ Extensible for future fields

---

