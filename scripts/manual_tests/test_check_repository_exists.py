#!/usr/bin/env python3
"""
Test suite for check_repository_exists() function.

Tests:
1. Non-existent repository - should return (False, None)
2. Existing repository - should return (True, repo_data)
3. Non-existent organization - should raise OrganizationNotFoundError
4. Empty repo name validation - should raise BaseAutomationError
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Load environment variables from .env file
#from dotenv import load_dotenv
#load_dotenv()

from src.integrations.github.repository_operations import check_repository_exists
from src.shared.exceptions import BaseAutomationError

print("=" * 70)
print("🧪 Testing check_repository_exists() Function")
print("=" * 70)
print()

# ==============================================================================
# TEST 1: Non-existent repository
# ==============================================================================
print("TEST 1: Non-existent repository")
print("-" * 70)

try:
    org = "Repo-Creation-Automation"
    repo_name = "this-repo-does-not-exist-abc-xyz-123"
    
    print(f"  🔹 Checking if repo exists: {org}/{repo_name}")
    
    exists, repo_data = check_repository_exists(
        org=org,
        repo_name=repo_name,
        correlation_id="test-1"
    )
    
    if not exists and repo_data is None:
        print(f"  ✅ PASS - Non-existent repo correctly returned (False, None)")
    else:
        print(f"  ❌ FAIL - Expected (False, None), got ({exists}, {repo_data})")
        
except Exception as e:
    print(f"  ❌ FAIL - Unexpected error: {type(e).__name__}: {str(e)[:100]}...")

print()

# ==============================================================================
# TEST 2: Existing repository
# ==============================================================================
print("TEST 2: Existing repository")
print("-" * 70)

try:
    org = "testorg-automation-1"
    # Use a repo that exists in your org - update this if needed
    repo_name = "asdfdsfdsfjdklsajf"  # This repo should exist
    
    print(f"  🔹 Checking if repo exists: {org}/{repo_name}")
    
    exists, repo_data = check_repository_exists(
        org=org,
        repo_name=repo_name,
        correlation_id="test-2"
    )
    
    if exists and repo_data is not None:
        print(f"  ✅ SUCCESS - Repository found!")
        print(f"     Name: {repo_data.get('name')}")
        print(f"     Full Name: {repo_data.get('full_name')}")
        print(f"     URL: {repo_data.get('html_url')}")
        print(f"     Private: {repo_data.get('private')}")
        print(f"     ID: {repo_data.get('id')}")
        
        # Verify required fields are present
        #TODO: can be changed
        required_fields = [
            'name', 'full_name', 'html_url', 'clone_url', 'ssh_url',
            'private', 'id', 'created_at', 'updated_at'
        ]

        # Optional fields (may not exist for newly created repos without commits)
        optional_fields = ['pushed_at', 'default_branch']

        missing_required = [field for field in required_fields if field not in repo_data]
        missing_optional = [field for field in optional_fields if field not in repo_data]

        if missing_required:
            print(f"  ❌ FAIL - Missing required fields: {missing_required}")
        else:
            print(f"  ✅ PASS - Existing repo correctly returned (True, repo_data) with all required fields")
            if missing_optional:
                print(f"     ℹ️  Note: Missing optional fields (expected for new repos): {missing_optional}")
    else:
        print(f"  ❌ FAIL - Expected repo to exist but got (False, None)")
        print(f"  ℹ️  Note: Make sure the repo '{repo_name}' exists in org '{org}'")
        
except Exception as e:
    print(f"  ❌ FAIL - Unexpected error: {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()

print()

# ==============================================================================
# TEST 3: Empty repo name validation
# ==============================================================================
print("TEST 3: Empty repo name validation")
print("-" * 70)

try:
    org = "Repo-Creation-Automation"
    repo_name = ""
    
    print(f"  🔹 Checking with empty repo name")
    
    exists, repo_data = check_repository_exists(
        org=org,
        repo_name=repo_name,
        correlation_id="test-4"
    )
    
    print(f"  ❌ FAIL - Should have raised BaseAutomationError for empty repo name")
    
except (BaseAutomationError, ValueError) as e:
    print(f"  ✅ PASS - Correctly raised error for empty repo name")
    print(f"     Error: {type(e).__name__}: {str(e)[:100]}...")
    
except Exception as e:
    print(f"  ⚠️  Got different error: {type(e).__name__}: {str(e)[:100]}...")

print()
print("=" * 70)
print("🎉 Tests completed!")
print("=" * 70)

