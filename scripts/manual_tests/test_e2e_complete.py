#!/usr/bin/env python3
"""
Complete End-to-End Integration Test
Tests the entire JIRA → GitHub workflow:
1. Fetch JIRA ticket
2. Extract data (Custom Fields OR JSON from description)
3. Validate repository data
4. Check if repository exists
5. Create repository (if needed)
6. Update JIRA with success/failure

Usage:
    python test_e2e_complete.py <JIRA_TICKET_ID> [--skip-create]

Examples:
    python test_e2e_complete.py RELB-7386  # Custom field extraction
    python test_e2e_complete.py RELB-6559  # JSON parsing from description
    python test_e2e_complete.py RELB-7386 --skip-create  # Test without creating repo
"""

import sys
import json
import re
import argparse
from typing import Dict, Any, Optional, Tuple
import os

# Force reload environment variables before importing anything
from dotenv import load_dotenv
load_dotenv(override=True)  # Override existing env vars with .env values

from src.integrations.jira.client import JiraClient, update_jira_success, update_jira_failure, update_jira_already_exists
from src.business.validators import validate_input, RepositoryRequest
from src.integrations.github.repository_operations import check_repository_exists
from src.integrations.github.repository_creator import create_github_repository
from src.observability import log_and_monitor, generate_correlation_id
from src.shared.exceptions import ValidationError, GitHubAPIError, JiraAPIError
from src.config import get_settings, reload_settings

# Force reload settings after .env is loaded
reload_settings()

# Debug: Print the transition settings to verify they're loaded
_debug_settings = get_settings()
print(f"\n🔧 Auto-transition settings loaded:")
print(f"   AUTO_TRANSITION_ON_SUCCESS: {_debug_settings.auto_transition_on_success}")
print(f"   SUCCESS_TRANSITION_NAME: {_debug_settings.success_transition_name}")
print(f"   SUCCESS_RESOLUTION: {_debug_settings.success_resolution or '(empty)'}\n")


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78 + "\n")


def extract_custom_fields(issue) -> Optional[Dict]:
    """
    Extract data from JIRA custom fields.

    This method is used for tickets created through JIRA forms that store
    data in custom fields rather than in the description.
    """
    settings = get_settings()

    if not settings.use_custom_fields:
        return None

    fields = issue.raw.get('fields', {})

    # Helper function to extract field value (handles CustomFieldOption objects and User objects)
    def get_field_value(field_id):
        value = fields.get(field_id)
        if value is None:
            return None
        # Handle JIRA User objects (VP, Director, EM fields)
        if isinstance(value, dict) and 'displayName' in value:
            return value['displayName']
        # Handle CustomFieldOption objects
        if hasattr(value, 'value'):
            return value.value
        # Handle dict with 'value' key
        if isinstance(value, dict) and 'value' in value:
            return value['value']
        # Handle simple values
        return str(value) if value else None

    # Extract all custom fields
    extracted = {
        'repo_name': get_field_value(settings.jira_field_repo_name),
        'github_org': get_field_value(settings.jira_field_github_org),
        'repo_type': get_field_value(settings.jira_field_repo_type) or 'Private',
        'code_type': get_field_value(settings.jira_field_code_type) or 'Python',
        'vp_name': get_field_value(settings.jira_field_vp_name),
        'director_name': get_field_value(settings.jira_field_director),
        'em_name': get_field_value(settings.jira_field_em_name),
        'product_line': get_field_value(settings.jira_field_product_line),
        # Use summary or description as repo description
        'description': fields.get('description') or fields.get('summary', ''),
        # Hardcoded values
        'department': 'crm',
    }

    # Check if we got required fields
    if not extracted['repo_name'] or not extracted['github_org']:
        return None

    return extracted


def parse_json_from_description(description: str) -> Optional[Dict]:
    """
    Extract JSON from JIRA ticket description.
    
    Supports:
    - JSON in code blocks: ```json {...} ```
    - Plain JSON in description
    """
    if not description:
        return None
    
    # Try to find JSON in code blocks first
    code_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    matches = re.findall(code_block_pattern, description, re.MULTILINE)
    
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON
    json_pattern = r'\{[\s\S]*"repository_details"[\s\S]*\}'
    matches = re.findall(json_pattern, description, re.MULTILINE)
    
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    return None


def flatten_json_structure(data: Dict) -> Dict:
    """
    Flatten nested JSON structure from JIRA to match RepositoryRequest model.
    
    Input format:
    {
        "repository_details": {...},
        "ownership_details": {...},
        "optional_metadata": {...}
    }
    
    Output: Flat dictionary matching RepositoryRequest fields
    """
    flattened = {}
    
    # Flatten repository_details
    if "repository_details" in data:
        for key, value in data["repository_details"].items():
            flattened[key] = value
    
    # Flatten ownership_details
    if "ownership_details" in data:
        for key, value in data["ownership_details"].items():
            flattened[key] = value
    
    # Flatten optional_metadata
    if "optional_metadata" in data:
        for key, value in data["optional_metadata"].items():
            flattened[key] = value
    
    return flattened


def test_jira_fetch(ticket_id: str, jira_client: JiraClient) -> Tuple[bool, Optional[Dict]]:
    """Test 1: Fetch JIRA ticket."""
    print_section("STEP 1: Fetch JIRA Ticket")

    try:
        issue = jira_client.client.issue(ticket_id)

        print(f"✅ Ticket found: {ticket_id}")
        print(f"   Summary: {issue.fields.summary}")
        print(f"   Status: {issue.fields.status}")
        print(f"   Reporter: {issue.fields.reporter.displayName}")
        print(f"   Type: {issue.fields.issuetype.name}")

        # Get description
        description = getattr(issue.fields, 'description', None)

        return True, {"issue": issue, "description": description}

    except Exception as e:
        print(f"❌ Failed to fetch ticket: {str(e)}")
        return False, None


def test_extract_data(issue, description: Optional[str]) -> Tuple[bool, Optional[Dict]]:
    """Test 2: Extract data from custom fields OR JSON description."""
    settings = get_settings()

    # Try custom fields first if enabled
    if settings.use_custom_fields:
        print_section("STEP 2: Extract Data from Custom Fields")

        print("Configuration:")
        print(f"  USE_CUSTOM_FIELDS: {settings.use_custom_fields}")
        print("")

        extracted_data = extract_custom_fields(issue)

        if extracted_data:
            print("✅ Successfully extracted data from custom fields!")
            print("   Extracted fields:")
            for key, value in extracted_data.items():
                if value and key not in ['description']:
                    print(f"   • {key}: {value}")
            return True, extracted_data
        else:
            print("⚠️  Custom fields extraction failed or incomplete")
            print("   Falling back to JSON parsing...")

    # Fall back to JSON parsing from description
    print_section("STEP 2: Parse JSON from Description")

    if not description:
        print("❌ No description available and custom fields not configured/empty")
        return False, None

    print("📋 Parsing JSON from description...")
    parsed_data = parse_json_from_description(description)

    if not parsed_data:
        print("❌ Failed to parse JSON from description")
        print("   Please ensure the description contains valid JSON")
        return False, None

    print("✅ Successfully parsed JSON from description!")
    print(f"   Found keys: {list(parsed_data.keys())}")

    # Flatten the structure
    print("\n🔄 Flattening nested structure...")
    flattened = flatten_json_structure(parsed_data)

    print("✅ Flattened data:")
    for key, value in flattened.items():
        if value and key not in ['documentation_link']:
            print(f"   • {key}: {value}")

    return True, flattened


def test_validate_data(flattened_data: Dict, ticket_id: str) -> Tuple[bool, Optional[RepositoryRequest]]:
    """Test 3: Validate repository data."""
    print_section("STEP 3: Validate Repository Data")

    # Add ticket_id to data
    flattened_data['jira_ticket_id'] = ticket_id

    

    

    try:
        validated = validate_input(flattened_data, correlation_id=None)

        print("✅ Validation passed")
        print(f"   Repo Name: {validated.repo_name}")
        print(f"   GitHub Org: {validated.github_org}")
        print(f"   Repo Type: {validated.repo_type}")
        print(f"   Code Type: {validated.code_type}")
        print(f"   VP: {validated.vp_name}")
        print(f"   Director: {validated.director_name}")
        print(f"   EM: {validated.em_name}")
        print(f"   Department: {validated.department}")

        return True, validated

    except ValidationError as e:
        print(f"❌ Validation failed: {e.message}")
        print(f"   Field: {e.field}")
        if e.expected_format:
            print(f"   Expected: {e.expected_format}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected validation error: {str(e)}")
        return False, None


def test_check_repo_exists(validated_data: RepositoryRequest, correlation_id: str) -> Tuple[bool, bool, Optional[Dict]]:
    """Test 4: Check if repository exists."""
    print_section("STEP 4: Check if Repository Exists")

    try:
        exists, repo_data = check_repository_exists(
            org=validated_data.github_org,
            repo_name=validated_data.repo_name,
            correlation_id=correlation_id
        )

        if exists:
            print(f"⚠️  Repository '{validated_data.repo_name}' already exists!")
            print(f"   URL: {repo_data.get('html_url')}")
            print(f"   Created: {repo_data.get('created_at')}")
            return True, True, repo_data
        else:
            print(f"✅ Repository '{validated_data.repo_name}' does not exist")
            print(f"   Ready to create in org: {validated_data.github_org}")
            return True, False, None

    except GitHubAPIError as e:
        print(f"❌ GitHub API error: {e.message}")
        print(f"   Status code: {e.status_code}")
        return False, False, None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False, False, None


def test_create_repository(validated_data: RepositoryRequest, correlation_id: str) -> Tuple[bool, Optional[Dict]]:
    """Test 5: Create GitHub repository."""
    print_section("STEP 5: Create GitHub Repository")

    try:
        print(f"🚀 Creating repository '{validated_data.repo_name}'...")
        print(f"   Organization: {validated_data.github_org}")
        print(f"   Type: {validated_data.repo_type}")
        print(f"   Description: {validated_data.description}")

        repo_data = create_github_repository(validated_data, correlation_id)

        print("\n✅ Repository created successfully!")
        print(f"   Name: {repo_data.get('name')}")
        print(f"   URL: {repo_data.get('html_url')}")
        print(f"   Clone URL: {repo_data.get('clone_url')}")
        print(f"   SSH URL: {repo_data.get('ssh_url')}")

        return True, repo_data

    except GitHubAPIError as e:
        print(f"❌ Repository creation failed: {e.message}")
        print(f"   Status code: {e.status_code}")
        if e.response_body:
            print(f"   Response: {e.response_body}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False, None


def test_update_jira_success(ticket_id: str, repo_data: Dict, correlation_id: str) -> bool:
    """Test 6: Update JIRA with success (repository created)."""
    print_section("STEP 6: Update JIRA with Success")

    try:
        print(f"📝 Updating JIRA ticket {ticket_id}...")

        success = update_jira_success(ticket_id, repo_data, correlation_id)

        if success:
            print("✅ JIRA ticket updated successfully!")
            print(f"   Comment added with repository details")
            print(f"   Labels added: repository-created, automated")
            print(f"   Check: https://hiyamodi.atlassian.net/browse/{ticket_id}")
        else:
            print("⚠️  JIRA update completed with warnings")

        return success

    except JiraAPIError as e:
        print(f"❌ JIRA update failed: {e.message}")
        print(f"   Status code: {e.status_code}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_update_jira_already_exists(ticket_id: str, repo_data: Dict, correlation_id: str) -> bool:
    """Test 6b: Update JIRA when repository already exists."""
    print_section("STEP 6: Update JIRA - Repository Already Exists")

    try:
        print(f"📝 Updating JIRA ticket {ticket_id} (repo already exists)...")

        success = update_jira_already_exists(ticket_id, repo_data, correlation_id)

        if success:
            print("✅ JIRA ticket updated successfully!")
            print(f"   Comment added: Repository already exists (idempotent)")
            print(f"   Labels added: repository-already-exists, automated")
            print(f"   Check: https://hiyamodi.atlassian.net/browse/{ticket_id}")
        else:
            print("⚠️  JIRA update completed with warnings")

        return success

    except JiraAPIError as e:
        print(f"❌ JIRA update failed: {e.message}")
        print(f"   Status code: {e.status_code}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_update_jira_failure(ticket_id: str, error_message: str, correlation_id: str) -> bool:
    """Test 7: Update JIRA with failure."""
    print_section("STEP 6: Update JIRA with Failure")

    try:
        print(f"📝 Updating JIRA ticket {ticket_id} with failure...")

        success = update_jira_failure(ticket_id, error_message, correlation_id)

        if success:
            print("✅ JIRA ticket updated with failure details")
            print(f"   Comment added with error message")
            print(f"   Labels added: repository-creation-failed, automated")
            print(f"   Check: https://hiyamodi.atlassian.net/browse/{ticket_id}")

        return success

    except Exception as e:
        print(f"❌ JIRA failure update failed: {str(e)}")
        return False


def main():
    """Main test execution."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="End-to-End Integration Test for JIRA → GitHub")
    parser.add_argument("ticket_id", help="JIRA ticket ID (e.g., RELB-6559)")
    parser.add_argument("--skip-create", action="store_true", help="Skip repository creation (dry run)")
    parser.add_argument("--force-create", action="store_true", help="Create repository even if exists")
    args = parser.parse_args()

    ticket_id = args.ticket_id
    skip_create = args.skip_create
    force_create = args.force_create

    # Generate correlation ID
    correlation_id = generate_correlation_id()

    print("\n" + "🧪" * 40)
    print("  END-TO-END INTEGRATION TEST: JIRA → GitHub")
    print("🧪" * 40)
    print(f"\n📋 Ticket ID: {ticket_id}")
    print(f"🔗 Correlation ID: {correlation_id}")
    if skip_create:
        print("⚠️  DRY RUN MODE: Repository creation will be skipped")

    # Track test results
    results = {
        "jira_fetch": False,
        "parse_description": False,
        "validate_data": False,
        "check_exists": False,
        "create_repo": False,
        "update_jira": False
    }

    # Step 1: Fetch JIRA ticket
    try:
        jira_client = JiraClient()
    except Exception as e:
        print_section("ERROR: JIRA Connection Failed")
        print(f"❌ Cannot connect to JIRA: {str(e)}")
        print("\n💡 Please check your .env file:")
        print("   - JIRA_URL")
        print("   - JIRA_EMAIL")
        print("   - JIRA_API_TOKEN")
        sys.exit(1)

    success, jira_data = test_jira_fetch(ticket_id, jira_client)
    results["jira_fetch"] = success

    if not success:
        print_section("❌ TEST FAILED: Cannot fetch JIRA ticket")
        sys.exit(1)

    # Step 2: Extract data (custom fields OR JSON from description)
    success, flattened_data = test_extract_data(jira_data["issue"], jira_data["description"])
    results["parse_description"] = success  # Keep same key for backward compatibility

    if not success:
        print_section("❌ TEST FAILED: Cannot extract data from ticket")
        print("\n💡 Data extraction failed. Please ensure either:")
        print("\n  Option 1: Custom Fields (recommended for JIRA forms)")
        print("    - Configure USE_CUSTOM_FIELDS=true in .env")
        print("    - Set custom field IDs in .env")
        print("    - Create ticket using JIRA form")
        print("\n  Option 2: JSON in Description (legacy)")
        print("    - Add JSON to ticket description in this format:")
        print("""
{
  "repository_details": {
    "repo_name": "my-service-name",
    "github_org": "my-org",
    "repo_type": "Private",
    "description": "My service description",
    "code_type": "Python"
  },
  "ownership_details": {
    "vp_name": "Hiya Modi",
    "director_name": "Hiya Modi",
    "em_name": "Bob Johnson",
    "product_line": "Platform",
    "department": "Engineering"
  }
}
""")
        sys.exit(1)

    # Step 3: Validate data
    success, validated_data = test_validate_data(flattened_data, ticket_id)
    results["validate_data"] = success

    if not success:
        print_section("❌ TEST FAILED: Data validation failed")
        error_msg = "Data validation failed. Please check the JIRA ticket description."
        test_update_jira_failure(ticket_id, error_msg, correlation_id)
        sys.exit(1)

    # Step 4: Check if repository exists
    success, repo_exists, existing_repo_data = test_check_repo_exists(validated_data, correlation_id)
    results["check_exists"] = success

    if not success:
        print_section("❌ TEST FAILED: Cannot check repository existence")
        error_msg = f"Failed to check if repository exists in organization {validated_data.github_org}"
        test_update_jira_failure(ticket_id, error_msg, correlation_id)
        sys.exit(1)

    # Step 5: Create repository (if needed)
    repo_data = None

    if repo_exists:
        if force_create:
            print("\n⚠️  --force-create specified, but repository already exists!")
            print("   Please delete the existing repository first or use a different name.")
            sys.exit(1)
        else:
            print("\n💡 Repository already exists - treating as success (idempotent)")
            repo_data = existing_repo_data
            results["create_repo"] = True

            # Step 6: Update JIRA with "already exists" message
            success = test_update_jira_already_exists(ticket_id, repo_data, correlation_id)
            results["update_jira"] = success
    else:
        if skip_create:
            print("\n⚠️  Skipping repository creation (--skip-create specified)")
            print_section("✅ DRY RUN COMPLETE")
            print("\n📊 Test Results:")
            for test, passed in results.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {test}")
            print("\n💡 Run without --skip-create to actually create the repository")
            sys.exit(0)
        else:
            success, repo_data = test_create_repository(validated_data, correlation_id)
            results["create_repo"] = success

            if not success:
                print_section("❌ TEST FAILED: Repository creation failed")
                error_msg = f"Failed to create repository {validated_data.repo_name} in organization {validated_data.github_org}"
                test_update_jira_failure(ticket_id, error_msg, correlation_id)
                sys.exit(1)

            # Step 6: Update JIRA with success (repository created)
            success = test_update_jira_success(ticket_id, repo_data, correlation_id)
            results["update_jira"] = success

    if not success:
        print("\n⚠️  JIRA update failed, but repository was created successfully")
        print(f"   Repository URL: {repo_data.get('html_url')}")

    # Print final summary
    print_section("✅ END-TO-END TEST COMPLETE!")

    print("📊 Test Results:")
    for test, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {test}")

    print(f"\n🎉 Success! Repository created and JIRA updated!")
    print(f"   Repository: {repo_data.get('html_url')}")
    print(f"   JIRA Ticket: https://hiyamodi.atlassian.net/browse/{ticket_id}")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
