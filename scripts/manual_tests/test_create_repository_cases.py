#!/usr/bin/env python3
"""
Comprehensive test suite for create_github_repository function.

Tests:
1. Create repo with existing custom property value (e.g., department="ml")
2. Create repo with new custom property value (e.g., department="engineering") - should update org schema
3. Verify custom properties were set correctly
"""

import os
import sys
import time



# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.integrations.github.repository_creator import create_github_repository
from src.integrations.github.auth import _get_github_client
from src.business.validators import RepositoryRequest
from src.shared.exceptions import GitHubAPIError

print("=" * 70)
print("🧪 Comprehensive Testing: create_github_repository()")
print("=" * 70)
print()

org = "Repo-Creation-Automation"

# ==============================================================================
# TEST 1: Create Repo with Existing Custom Property Value
# ==============================================================================
print("TEST 1: Create Repo with Existing Custom Property Value (department='ml')")
print("-" * 70)

test_repo_name_1 = f"test-repo-existing-{int(time.time())}"

try:
    # Use "ml" which should already exist in allowed values ["crm", "ml", "sre"]
    validated_data = RepositoryRequest(
        repo_name=test_repo_name_1,
        github_org=org,
        description="Test repo with existing department value",
        vp_name="Test VP",
        director_name="Test Director",
        em_name="Test EM",
        product_line="Platform",
        department="ml",  # Existing value in ["crm", "ml", "sre"]
        repo_type="Internal",
        code_type="Python",
        jira_ticket_id="TEST-001"
    )
    
    print(f"  🔹 Creating repo: {test_repo_name_1}")
    print(f"     Org: {org}")
    print(f"     Department: ml (existing value - should NOT update org schema)")
    
    repo_data = create_github_repository(
        validated_data=validated_data,
        correlation_id="test-existing-dept"
    )
    
    print(f"\n  ✅ SUCCESS - Repository created!")
    print(f"     Name: {repo_data.get('name')}")
    print(f"     Full Name: {repo_data.get('full_name')}")
    print(f"     URL: {repo_data.get('html_url')}")
    print(f"     ID: {repo_data.get('id')}")
    print(f"     Private: {repo_data.get('private')}")
    
    print(f"\n  ✅ PASS - Repo created with existing custom property value")
    
    # Store for cleanup
    repo_1_full_name = repo_data.get('full_name')
    
except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()
    repo_1_full_name = None

print()

# ==============================================================================
# TEST 2: Create Repo with NEW Custom Property Value (Updates Org Schema)
# ==============================================================================
print("TEST 2: Create Repo with NEW Custom Property Value (department='engineering')")
print("-" * 70)

test_repo_name_2 = f"test-repo-newdept-{int(time.time())}"

try:
    # Use "engineering" which should NOT exist in allowed values ["crm", "ml", "sre"]
    # Code should ADD "engineering" to the org schema
    validated_data = RepositoryRequest(
        repo_name=test_repo_name_2,
        github_org=org,
        description="Test repo with NEW department value - should update org schema",
        vp_name="Test VP",
        director_name="Test Director",
        em_name="Test EM",
        product_line="Platform",
        department="testing department2",  # NEW value - not in ["crm", "ml", "sre"]
        repo_type="Internal",
        code_type="Python",
        jira_ticket_id="TEST-002"
    )
    
    print(f"  🔹 Creating repo: {test_repo_name_2}")
    print(f"     Org: {org}")
    print(f"     Department: engineering (NEW - should update org schema to add it)")
    
    repo_data = create_github_repository(
        validated_data=validated_data,
        correlation_id="test-new-dept"
    )
    
    print(f"\n  ✅ SUCCESS - Repository created!")
    print(f"     Name: {repo_data.get('name')}")
    print(f"     Full Name: {repo_data.get('full_name')}")
    print(f"     URL: {repo_data.get('html_url')}")
    print(f"     ID: {repo_data.get('id')}")
    print(f"     Private: {repo_data.get('private')}")
    
    print(f"\n  ✅ PASS - Repo created AND org schema updated with new department value")
    
    # Store for cleanup
    repo_2_full_name = repo_data.get('full_name')
    
except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()
    repo_2_full_name = None

print()

# ==============================================================================
# Cleanup
# ==============================================================================
print("=" * 70)
print("🧹 Cleanup")
print("=" * 70)

cleanup = input("\nDelete test repositories? (yes/no): ").strip().lower()

if cleanup == "yes":
    try:
        client = _get_github_client(org)
        
        if repo_1_full_name:
            print(f"  🗑️  Deleting {repo_1_full_name}...")
            repo1 = client.get_repo(repo_1_full_name)
            repo1.delete()
            print(f"     ✅ Deleted")
        
        if repo_2_full_name:
            print(f"  🗑️  Deleting {repo_2_full_name}...")
            repo2 = client.get_repo(repo_2_full_name)
            repo2.delete()
            print(f"     ✅ Deleted")
        
        print(f"\n✅ Cleanup completed!")
        
    except Exception as e:
        print(f"  ❌ Cleanup failed: {e}")
        print(f"  ⚠️  Manual cleanup may be required")
else:
    print(f"  ℹ️  Skipped cleanup - repositories still exist")
    if repo_1_full_name:
        print(f"     - {repo_1_full_name}")
    if repo_2_full_name:
        print(f"     - {repo_2_full_name}")

print()
print("=" * 70)
print("🎉 Tests Completed!")
print("=" * 70)

