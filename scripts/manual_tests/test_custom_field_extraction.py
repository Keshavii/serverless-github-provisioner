#!/usr/bin/env python3
"""
Test Custom Field Extraction for JIRA Tickets

This script tests the custom field extraction logic with real JIRA tickets.
Specifically designed for testing ticket RELB-7386 and similar form-based tickets.

Usage:
    python test_custom_field_extraction.py <TICKET_ID>

Example:
    python test_custom_field_extraction.py RELB-7386
"""

import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_settings
from src.integrations.jira.client import JiraClient
from src.shared.exceptions import JiraAPIError


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_fetch_ticket(ticket_id):
    """Test 1: Fetch Ticket from JIRA"""
    print_section(f"TEST 1: Fetch Ticket - {ticket_id}")

    try:
        client = JiraClient()
        issue = client.client.issue(ticket_id)

        print(f"✅ Successfully retrieved ticket: {ticket_id}")
        print(f"   Summary: {issue.fields.summary}")
        print(f"   Status: {issue.fields.status.name}")
        print(f"   Type: {issue.fields.issuetype.name}")
        print(f"   Reporter: {issue.fields.reporter.displayName if issue.fields.reporter else 'N/A'}")

        return issue
    except Exception as e:
        print(f"❌ Failed to fetch ticket: {str(e)}")
        return None


def test_extract_custom_fields(issue):
    """Test 2: Extract Custom Fields"""
    print_section("TEST 2: Extract Custom Fields")

    settings = get_settings()

    print("Configuration:")
    print(f"  USE_CUSTOM_FIELDS: {settings.use_custom_fields}")
    print()

    if not settings.use_custom_fields:
        print("⚠️  Warning: USE_CUSTOM_FIELDS is set to False")
        print("   Update .env to set USE_CUSTOM_FIELDS=true")
        return None

    # Extract custom fields
    fields = {}
    field_mapping = {
        'repo_name': settings.jira_field_repo_name,
        'github_org': settings.jira_field_github_org,
        'repo_type': settings.jira_field_repo_type,
        'code_type': settings.jira_field_code_type,
        'vp_name': settings.jira_field_vp_name,
        'director_name': settings.jira_field_director,
        'em_name': settings.jira_field_em_name,
        'product_line': settings.jira_field_product_line,
    }

    print("Extracting fields:")
    for field_name, field_id in field_mapping.items():
        try:
            value = getattr(issue.fields, field_id, None)
            fields[field_name] = value
            status = "✅" if value else "⚠️ "
            print(f"  {status} {field_name:15} ({field_id}): {value}")
        except Exception as e:
            print(f"  ❌ {field_name:15} ({field_id}): Error - {str(e)}")
            fields[field_name] = None

    return fields


def test_webhook_simulation(issue, fields):
    """Test 3: Simulate Webhook Payload Processing"""
    print_section("TEST 3: Simulate Webhook Payload")

    # Create a simulated webhook payload
    payload = {
        "timestamp": 1743916636542,
        "webhookEvent": "jira:issue_created",
        "issue_event_type_name": "issue_created",
        "issue": {
            "key": issue.key,
            "fields": {
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "issuetype": {
                    "name": issue.fields.issuetype.name
                },
                "status": {
                    "name": issue.fields.status.name
                },
                "labels": issue.fields.labels or [],
                "reporter": {
                    "emailAddress": issue.fields.reporter.emailAddress if issue.fields.reporter else None
                }
            }
        }
    }

    # Add custom fields to payload (convert to strings to avoid serialization issues)
    settings = get_settings()
    payload["issue"]["fields"][settings.jira_field_repo_name] = str(fields.get('repo_name', ''))
    payload["issue"]["fields"][settings.jira_field_github_org] = str(fields.get('github_org', ''))
    payload["issue"]["fields"][settings.jira_field_repo_type] = str(fields.get('repo_type', ''))
    payload["issue"]["fields"][settings.jira_field_code_type] = str(fields.get('code_type', ''))
    payload["issue"]["fields"][settings.jira_field_vp_name] = str(fields.get('vp_name', ''))
    payload["issue"]["fields"][settings.jira_field_director] = str(fields.get('director_name', ''))
    payload["issue"]["fields"][settings.jira_field_em_name] = str(fields.get('em_name', ''))
    payload["issue"]["fields"][settings.jira_field_product_line] = str(fields.get('product_line', ''))

    print("Simulated webhook payload:")
    print(json.dumps(payload, indent=2))
    print(f"\n✅ Webhook payload created successfully")
    print(f"   Contains {len(fields)} extracted custom fields")

    return payload





def run_all_tests(ticket_id):
    """Run all tests for custom field extraction."""
    print("\n" + "🧪" * 40)
    print(f"  CUSTOM FIELD EXTRACTION TEST")
    print(f"  Ticket: {ticket_id}")
    print("🧪" * 40)

    # Test 1: Fetch ticket
    issue = test_fetch_ticket(ticket_id)
    if not issue:
        print("\n❌ Cannot continue - failed to fetch ticket")
        return False

    # Test 2: Extract custom fields
    fields = test_extract_custom_fields(issue)
    if not fields:
        print("\n❌ Cannot continue - custom field extraction not enabled")
        return False

    # Test 3: Simulate webhook
    payload = test_webhook_simulation(issue, fields)

    # Validate extracted data
    print_section("VALIDATION SUMMARY")

    required_fields = ['repo_name', 'github_org', 'repo_type', 'code_type']
    optional_fields = ['vp_name', 'director_name', 'em_name', 'product_line']

    missing_required = []
    present_optional = []

    for field in required_fields:
        if not fields.get(field):
            missing_required.append(field)

    for field in optional_fields:
        if fields.get(field):
            present_optional.append(field)

    if missing_required:
        print(f"❌ Missing required fields: {', '.join(missing_required)}")
        print("\nThis ticket cannot be processed for repository creation.")
        return False
    else:
        print(f"✅ All required fields present!")
        print(f"   • Repository: {fields['repo_name']}")
        print(f"   • Organization: {fields['github_org']}")
        print(f"   • Type: {fields['repo_type']}")
        print(f"   • Code Type: {fields['code_type']}")

    if present_optional:
        print(f"\n✅ Optional fields present:")
        for field in present_optional:
            print(f"   • {field}: {fields[field]}")

    print(f"\n{'='*80}")
    print("✅ TICKET IS READY FOR PROCESSING!")
    print(f"{'='*80}")
    print("\nExpected behavior when this ticket is processed:")
    print(f"  1. Webhook handler will extract data from custom fields")
    print(f"  2. Repository '{fields['repo_name']}' will be created in '{fields['github_org']}'")
    print(f"  3. Repository will be set to '{fields['repo_type']}' visibility")
    print(f"  4. Metadata will include ownership details")
    print(f"  5. JIRA ticket will be updated with repository URL on success")

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Error: Missing JIRA ticket ID")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <TICKET_ID>")
        print("\nExample:")
        print(f"  python {sys.argv[0]} RELB-7386")
        sys.exit(1)

    ticket_id = sys.argv[1].strip()

    success = run_all_tests(ticket_id)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
