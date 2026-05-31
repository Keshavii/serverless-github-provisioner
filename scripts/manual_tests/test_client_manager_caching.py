#!/usr/bin/env python3
"""
Test suite for GitHubClientManager caching and multi-org support.

Tests:
1. Client caching - verify same client object is returned for multiple calls
2. Multi-org support - verify cache stores clients per organization
3. Token expiry - verify new client is created after token expires
4. Installation ID caching - verify installation IDs are cached
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.integrations.github.auth import GitHubClientManager

print("=" * 70)
print("🧪 Testing GitHubClientManager Caching & Multi-Org Support")
print("=" * 70)
print()

# Create a fresh manager instance
manager = GitHubClientManager()

# ==============================================================================
# TEST 1: Client Caching - Multiple Calls for Same Org
# ==============================================================================
print("TEST 1: Client Caching - Multiple Calls for Same Org")
print("-" * 70)

org = "Repo-Creation-Automation"

try:
    print(f"  🔹 Call #1: get_client('{org}')")
    client1 = manager.get_client(org)
    client1_id = id(client1)
    print(f"     ✅ Client created")
    print(f"     📌 Client ID: {client1_id}")
    print(f"     📊 Cached orgs: {list(manager._clients.keys())}")
    print(f"     ⏰ Token expires at: {manager._token_expiry[org]}")
    print()
    
    print(f"  🔹 Call #2: get_client('{org}')")
    client2 = manager.get_client(org)
    client2_id = id(client2)
    print(f"     📌 Client ID: {client2_id}")
    print()
    
    print(f"  🔹 Call #3: get_client('{org}')")
    client3 = manager.get_client(org)
    client3_id = id(client3)
    print(f"     📌 Client ID: {client3_id}")
    print()
    
    print(f"  🔹 Call #4: get_client('{org}')")
    client4 = manager.get_client(org)
    client4_id = id(client4)
    print(f"     📌 Client ID: {client4_id}")
    print()
    
    print(f"  🔹 Call #5: get_client('{org}')")
    client5 = manager.get_client(org)
    client5_id = id(client5)
    print(f"     📌 Client ID: {client5_id}")
    print()
    
    # Verify all clients are the same object
    if (client1 is client2 is client3 is client4 is client5):
        print(f"  ✅ PASS - All 5 calls returned the SAME client object (caching works!)")
        print(f"     All IDs match: {client1_id}")
    else:
        print(f"  ❌ FAIL - Different client objects returned (caching broken)")
        print(f"     IDs: {client1_id}, {client2_id}, {client3_id}, {client4_id}, {client5_id}")
    
except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()

print()

# ==============================================================================
# TEST 2: Multi-Org Support
# ==============================================================================
print("TEST 2: Multi-Org Support")
print("-" * 70)

try:
    org1 = "Repo-Creation-Automation"
    org2 = "testorg-automation-1"

    print(f"  🔹 get_client('{org1}')")
    client1 = manager.get_client(org1)
    client1_id = id(client1)
    print(f"     ✅ Client created: {client1_id}")
    print()

    print(f"  🔹 get_client('{org2}')")
    client2 = manager.get_client(org2)
    client2_id = id(client2)
    print(f"     ✅ Client created: {client2_id}")
    print()

    print(f"  📊 Current state:")
    print(f"     Cached clients: {list(manager._clients.keys())}")
    print(f"     Installation IDs: {manager._installation_ids}")
    print()

    # Verify different clients for different orgs
    if client1 is not client2:
        print(f"  ✅ PASS - Different clients for different orgs")
        print(f"     {org1}: {client1_id}")
        print(f"     {org2}: {client2_id}")
    else:
        print(f"  ❌ FAIL - Same client returned for different orgs")
    print()

    # Verify both orgs are cached
    if org1 in manager._clients and org2 in manager._clients:
        print(f"  ✅ PASS - Both orgs cached")
    else:
        print(f"  ❌ FAIL - Not all orgs cached")
    print()

    print(f"  🔹 Attempting get_client('non-existent-org-xyz') - should fail")
    try:
        bad_client = manager.get_client('non-existent-org-xyz')
        print(f"     ❌ FAIL - Should have raised error for non-existent org")
    except Exception as e:
        print(f"     ✅ PASS - Correctly rejected non-existent org")
        print(f"     Error: {str(e)[:100]}...")

except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()

print()

# ==============================================================================
# TEST 3: Token Expiry Simulation
# ==============================================================================
print("TEST 3: Token Expiry Simulation")
print("-" * 70)

try:
    print(f"  🔹 Get initial client for '{org}'")
    client1 = manager.get_client(org)
    client1_id = id(client1)
    print(f"     Client ID: {client1_id}")
    print(f"     Expires at: {manager._token_expiry[org]}")
    print()

    print(f"  🔹 Manually expire the token")
    # Set expiry to now - 1 second (using datetime)
    from datetime import datetime, timedelta
    manager._token_expiry[org] = datetime.now() - timedelta(seconds=1)
    print(f"     New expires_at: {manager._token_expiry[org]} (expired)")
    print()

    print(f"  🔹 Call get_client again - should create NEW client")
    client2 = manager.get_client(org)
    client2_id = id(client2)
    print(f"     Client ID: {client2_id}")
    print(f"     Expires at: {manager._token_expiry[org]}")
    print()
    
    if client1 is not client2:
        print(f"  ✅ PASS - New client created after token expiry")
        print(f"     Old ID: {client1_id}")
        print(f"     New ID: {client2_id}")
    else:
        print(f"  ❌ FAIL - Same client returned despite expired token")
    
except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()

print()

# ==============================================================================
# TEST 4: Installation ID Caching
# ==============================================================================
print("TEST 4: Installation ID Caching")
print("-" * 70)

try:
    org1 = "Repo-Creation-Automation"
    org2 = "testorg-automation-1"

    print(f"  🔹 Check installation ID cache")
    print(f"     Installation IDs: {manager._installation_ids}")
    print()

    # Check org1
    if org1 in manager._installation_ids:
        installation_id1 = manager._installation_ids[org1]
        print(f"  ✅ Installation ID cached for '{org1}': {installation_id1}")
    else:
        print(f"  ❌ FAIL - Installation ID not cached for '{org1}'")
    print()

    # Check org2
    if org2 in manager._installation_ids:
        installation_id2 = manager._installation_ids[org2]
        print(f"  ✅ Installation ID cached for '{org2}': {installation_id2}")
    else:
        print(f"  ❌ FAIL - Installation ID not cached for '{org2}'")
    print()

    # Summary - verify both orgs are cached
    orgs_cached = org1 in manager._installation_ids and org2 in manager._installation_ids

    if orgs_cached and len(manager._installation_ids) == 2:
        print(f"  ✅ PASS - Both installation IDs cached correctly")
        print(f"     {org1}: {manager._installation_ids[org1]}")
        print(f"     {org2}: {manager._installation_ids[org2]}")
    else:
        print(f"  ❌ FAIL - Installation ID caching issue")
        print(f"     Expected 2 orgs cached, got {len(manager._installation_ids)}")
        print(f"     Cached orgs: {list(manager._installation_ids.keys())}")

except Exception as e:
    print(f"  ❌ FAIL - {type(e).__name__}: {str(e)[:150]}...")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("🎉 Tests completed!")
print("=" * 70)

