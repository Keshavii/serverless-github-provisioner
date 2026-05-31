#!/usr/bin/env python3
"""
Fetch JIRA ticket RELB-7386 and display all fields
"""

import os
import sys
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
    print("Fetching ticket RELB-7386...")
    issue = jira_client.issue('RELB-7386')
    
    # Print all available fields
    print('=' * 80)
    print(f'TICKET: {issue.key}')
    print('=' * 80)
    print()
    
    print('BASIC FIELDS:')
    print(f'  Summary: {issue.fields.summary}')
    print(f'  Status: {issue.fields.status.name}')
    print(f'  Issue Type: {issue.fields.issuetype.name}')
    print(f'  Reporter: {issue.fields.reporter.displayName if issue.fields.reporter else "N/A"}')
    print(f'  Created: {issue.fields.created}')
    print(f'  Updated: {issue.fields.updated}')
    print()
    
    print('LABELS:')
    labels = issue.fields.labels or []
    if labels:
        for label in labels:
            print(f'  - {label}')
    else:
        print('  (No labels)')
    print()
    
    print('DESCRIPTION:')
    print('-' * 80)
    description = issue.fields.description or '(No description)'
    print(description)
    print('-' * 80)
    print()
    
    print('ALL FIELD NAMES:')
    field_names = []
    for field_name in dir(issue.fields):
        if not field_name.startswith('_'):
            try:
                value = getattr(issue.fields, field_name)
                if value is not None and not callable(value):
                    field_names.append(field_name)
            except:
                pass
    
    for fname in sorted(field_names):
        print(f'  - {fname}')
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

