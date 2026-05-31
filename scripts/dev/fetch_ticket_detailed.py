#!/usr/bin/env python3
"""
Fetch JIRA ticket RELB-7386 with detailed custom fields
"""

import os
import sys
import json
from dotenv import load_dotenv
from jira import JIRA

# Load environment variables
load_dotenv()

# Get credentials
jira_url = os.getenv('JIRA_URL')
jira_email = os.getenv('JIRA_EMAIL')
jira_token = os.getenv('JIRA_API_TOKEN')

if not all([jira_url, jira_email, jira_token]):
    print('ERROR: JIRA credentials not found in .env file')
    sys.exit(1)

try:
    # Connect to JIRA
    print("Connecting to JIRA...")
    jira_client = JIRA(
        server=jira_url,
        basic_auth=(jira_email, jira_token),
        timeout=30
    )
    
    # Fetch ticket
    print("Fetching ticket RELB-7386...\n")
    issue = jira_client.issue('RELB-7386')
    
    print('=' * 80)
    print(f'TICKET: {issue.key}')
    print('=' * 80)
    print()
    
    print('BASIC FIELDS:')
    print(f'  Summary: {issue.fields.summary}')
    print(f'  Status: {issue.fields.status.name}')
    print(f'  Issue Type: {issue.fields.issuetype.name}')
    print(f'  Reporter: {issue.fields.reporter.displayName if issue.fields.reporter else "N/A"}')
    print(f'  Labels: {issue.fields.labels}')
    print()
    
    print('DESCRIPTION:')
    print('-' * 80)
    print(issue.fields.description or '(No description)')
    print('-' * 80)
    print()
    
    print('CUSTOM FIELDS (Non-null values):')
    print('-' * 80)
    
    # List all custom fields with values
    custom_fields = {}
    for field_name in dir(issue.fields):
        if field_name.startswith('customfield_'):
            try:
                value = getattr(issue.fields, field_name)
                if value is not None:
                    # Try to format complex objects
                    if hasattr(value, '__dict__'):
                        # Convert object to dict
                        value_str = str(value)
                    elif isinstance(value, (list, dict)):
                        value_str = json.dumps(value, indent=2)
                    else:
                        value_str = str(value)
                    
                    custom_fields[field_name] = value_str
                    print(f'\n{field_name}:')
                    print(f'  {value_str}')
            except:
                pass
    
    print()
    print('=' * 80)
    print(f'Total custom fields with data: {len(custom_fields)}')
    print('=' * 80)
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

