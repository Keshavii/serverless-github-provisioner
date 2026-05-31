#!/usr/bin/env python3
"""
Test script to verify webhook failure handling and JIRA updates.

This script simulates webhook failures to test that JIRA tickets
are properly updated with error comments and transitioned to Manual Review.

Usage:
    python test_webhook_failure.py <JIRA_TICKET_ID>
    
Example:
    python test_webhook_failure.py RELB-7452
"""

import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

from src.config import reload_settings, get_settings
from src.handlers.github_handler import _update_jira_on_webhook_failure

# Force reload settings
reload_settings()


def test_webhook_failure_update(ticket_id: str):
    """Test JIRA update on webhook failure."""
    
    print("\n" + "="*80)
    print("  TEST: Webhook Failure JIRA Update")
    print("="*80)
    
    print(f"\n📋 Ticket ID: {ticket_id}")
    
    # Display settings
    settings = get_settings()
    print(f"\n🔧 Settings:")
    print(f"   AUTO_TRANSITION_ON_WEBHOOK_FAILURE: {settings.auto_transition_on_webhook_failure}")
    print(f"   WEBHOOK_FAILURE_TRANSITION_NAME: {settings.webhook_failure_transition_name}")
    print(f"   WEBHOOK_FAILURE_RESOLUTION: {settings.webhook_failure_resolution or '(empty)'}")
    
    # Simulate webhook failure
    print(f"\n🧪 Simulating webhook validation failure...")
    
    correlation_id = "test-webhook-failure-12345"
    
    result = _update_jira_on_webhook_failure(
        ticket_id=ticket_id,
        error_type="Test Webhook Validation Error",
        error_message="This is a test error to verify JIRA update functionality. The webhook payload was invalid.",
        correlation_id=correlation_id
    )
    
    if result:
        print(f"\n✅ JIRA ticket updated successfully!")
        print(f"   Comment added with error details")
        print(f"   Labels added: webhook-validation-failed, automated, requires-manual-review")
        
        if settings.auto_transition_on_webhook_failure:
            print(f"   Ticket transitioned to: {settings.webhook_failure_transition_name}")
        
        print(f"\n🔗 Check ticket: https://hiyamodi.atlassian.net/browse/{ticket_id}")
    else:
        print(f"\n❌ Failed to update JIRA ticket")
        print(f"   Check logs for details")
    
    print("\n" + "="*80)
    print("  TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_webhook_failure.py <JIRA_TICKET_ID>")
        print("Example: python test_webhook_failure.py RELB-7452")
        sys.exit(1)
    
    ticket_id = sys.argv[1]
    test_webhook_failure_update(ticket_id)

