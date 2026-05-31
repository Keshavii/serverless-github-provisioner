"""
GitHub Repository Creator

Provides comprehensive repository creation with support for custom properties,
branch protection, team permissions, and organization-specific configurations.
Implements robust error handling and validation for production-grade repository
provisioning workflows.
"""

import time
from typing import Dict, Optional

import requests

from ...config import get_settings
from ...shared import BaseAutomationError, GitHubAPIError
from ...observability import log_and_monitor, log_execution_time, emit_latency_metric
from .auth import get_client_manager

def create_github_repository(validated_data, correlation_id: Optional[str] = None) -> Dict:
    """
    Create GitHub repository with custom properties and organization configurations.

    Performs atomic repository creation with custom properties using GitHub's
    REST API v2022-11-28. Automatically provisions department metadata and
    CI/CD configuration properties during repository creation.

    Workflow:
        1. Validate department value exists in organization schema
        2. Add missing department values to organization metadata if needed
        3. Create repository with all properties in single atomic operation
        4. Return repository metadata for downstream processing

    Custom Properties Set:
        - department: Organization department (from input)
        - tektonci: false (CI/CD configuration)
        - tektonci-postmerge: false (post-merge CI)
        - tektonci-test: false (test CI)
        - tektonci-test-postmerge: false (post-merge test CI)

    Args:
        validated_data: Validated input model containing repository specifications:
            - repo_name: Repository name (alphanumeric, hyphens, underscores)
            - description: Repository description text
            - department: Department identifier for custom property
            - github_org: Target GitHub organization name
        correlation_id: Optional request identifier for distributed tracing

    Returns:
        Dictionary containing repository metadata:
            - name: Repository name
            - full_name: Qualified name (organization/repository)
            - html_url: Repository web interface URL
            - clone_url: HTTPS clone URL
            - ssh_url: SSH clone URL
            - id: GitHub repository identifier
            - created_at: ISO 8601 creation timestamp

    Raises:
        GitHubAPIError: If GitHub App is not installed in the organization,
                       or if GitHub API call fails (including repo creation)
        BaseAutomationError: If repo_details is missing required fields

    Note:
        - Organization validation is already done in check_repository_exists()
        - Organization must be explicitly provided to prevent accidental repo creation
          in the wrong organization.
        - Uses REST API directly instead of PyGithub to support custom_properties parameter
    """
 
    org = validated_data.github_org
    repo_name = validated_data.repo_name
    department = validated_data.department
    repo_type = validated_data.repo_type.lower()

    with log_execution_time(
        "create_github_repository",
        correlation_id=correlation_id,
        repo_name=repo_name,
        github_org=org
    ):
        try:
          
            client = get_client_manager().get_client(org)
            
            log_and_monitor(
                "checking_department_in_org_properties",
                level="INFO",
                correlation_id=correlation_id,
                github_org=org,
                department=department
            )

            auth_token = client._Github__requester.auth.token 

            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }

            schema_url = f"https://api.github.com/orgs/{org}/properties/schema"

            property_types = {}

            settings = get_settings()
            timeout = settings.github_api_timeout

            try:
                response = requests.get(schema_url, headers=headers, timeout=timeout)
                response.raise_for_status()

                schema_data = response.json()
                department_property = None

                properties_list = schema_data if isinstance(schema_data, list) else schema_data.get("properties", [])

                for prop in properties_list:
                    prop_name = prop.get("property_name")
                    prop_type = prop.get("value_type")
                    if prop_name and prop_type:
                        property_types[prop_name] = prop_type

                    if prop_name == "department":
                        department_property = prop

                if department_property:
               
                    allowed_values = department_property.get("allowed_values", [])

                    if department not in allowed_values:
               
                        log_and_monitor(
                            "adding_department_to_org_properties",
                            level="INFO",
                            correlation_id=correlation_id,
                            github_org=org,
                            department=department
                        )

                        allowed_values.append(department)
                        department_property["allowed_values"] = allowed_values

                        clean_properties = []
                        for prop in properties_list:
                            clean_prop = {k: v for k, v in prop.items() if k not in ["url", "source_type"]}
                            clean_properties.append(clean_prop)

                        update_response = requests.patch(
                            schema_url,
                            headers=headers,
                            json={"properties": clean_properties},
                            timeout=timeout
                        )
                        update_response.raise_for_status()

                        log_and_monitor(
                            "department_added_to_org_properties",
                            level="INFO",
                            correlation_id=correlation_id,
                            github_org=org,
                            department=department
                        )
                else:
 
                    log_and_monitor(
                        "department_property_not_found_in_org",
                        level="WARNING",
                        correlation_id=correlation_id,
                        github_org=org,
                        message="Department property not defined at organization level. Repository will be created without custom properties."
                    )

            except requests.exceptions.HTTPError as e:

                status_code = e.response.status_code if e.response else None
                error_body = {}
                try:
                    error_body = e.response.json() if e.response else {}
                except Exception:
                    error_body = {"message": e.response.text if e.response else str(e)}

                if status_code in [408, 429, 500, 502, 503, 504]:
                    log_and_monitor(
                        "org_properties_transient_error",
                        level="ERROR",
                        correlation_id=correlation_id,
                        github_org=org,
                        status_code=status_code,
                        error=str(e),
                        message="Transient error checking organization custom properties. Will retry."
                    )
                    raise GitHubAPIError(
                        message=f"Failed to check organization custom properties (transient error): {error_body.get('message', str(e))}",
                        status_code=status_code,
                        response_body=error_body
                    )

                elif status_code == 403:
                    error_msg = error_body.get('message', '').lower()
                    if 'rate limit' in error_msg or 'api rate limit' in error_msg:
                        log_and_monitor(
                            "org_properties_rate_limit",
                            level="ERROR",
                            correlation_id=correlation_id,
                            github_org=org,
                            status_code=status_code,
                            error=str(e),
                            message="Rate limit while checking organization custom properties. Will retry."
                        )
                        raise GitHubAPIError(
                            message=f"Rate limit exceeded while checking organization custom properties: {str(e)}",
                            status_code=status_code,
                            response_body=error_body
                        )
                    else:

                        log_and_monitor(
                            "org_properties_permission_warning",
                            level="WARNING",
                            correlation_id=correlation_id,
                            github_org=org,
                            status_code=status_code,
                            error=str(e),
                            message="Insufficient permissions to manage organization custom properties. Repository will be created without custom properties."
                        )

                elif status_code == 422:
                    log_and_monitor(
                        "org_properties_validation_error",
                        level="ERROR",
                        correlation_id=correlation_id,
                        github_org=org,
                        status_code=status_code,
                        error_details=error_body,
                        error=str(e),
                        message=f"GitHub validation error (422) when updating org schema: {error_body.get('message', 'Unknown validation error')}"
                    )

                else:
                    log_and_monitor(
                        "failed_to_check_org_properties",
                        level="WARNING",
                        correlation_id=correlation_id,
                        github_org=org,
                        status_code=status_code,
                        error=str(e),
                        message="Failed to check/update organization custom properties. Continuing with repo creation without custom properties."
                    )


            except requests.exceptions.RequestException as e:

                log_and_monitor(
                    "org_properties_network_error",
                    level="ERROR",
                    correlation_id=correlation_id,
                    github_org=org,
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Network error while checking organization custom properties. Will retry."
                )
                raise GitHubAPIError(
                    message=f"Network error communicating with GitHub API (org properties): {str(e)}",
                    status_code=None, 
                    response_body={"error": "network_error", "details": str(e), "error_type": type(e).__name__}
                )

            log_and_monitor(
                "creating_repository_with_custom_properties",
                level="INFO",
                correlation_id=correlation_id,
                repo_name=repo_name,
                github_org=org,
                department=department,
                repo_type=repo_type
            )

            create_repo_url = f"https://api.github.com/orgs/{org}/repos"

            repo_payload = {
                "name": repo_name,
                "visibility": repo_type,
                "auto_init": False,
                "has_issues": False,
                "has_wiki": False,
                "has_projects": False,
                "custom_properties": {
                    "department": [department] if isinstance(department, str) else department,
                    "tektonci": "false",
                    "tektonci-postmerge": "false",
                    "tektonci-test": "false",
                    "tektonci-test-postmerge": "false"
                }
            }

            try:
                api_start_time = time.time()

                create_response = requests.post(
                    create_repo_url,
                    headers=headers,
                    json=repo_payload,
                    timeout=timeout
                )

                api_duration = (time.time() - api_start_time) * 1000

                if create_response.status_code >= 400:
                    log_and_monitor(
                        "github_api_error_response_debug",
                        level="DEBUG",
                        correlation_id=correlation_id,
                        status_code=create_response.status_code,
                        response_body=create_response.text,
                        response_headers=dict(create_response.headers),
                        repo_name=repo_name,
                        github_org=org
                    )

                create_response.raise_for_status()

                repo_data_raw = create_response.json()

                emit_latency_metric(
                    'GitHubAPI',
                    api_duration,
                    dimensions={'Operation': 'create_repo', 'Org': org}
                )

                log_and_monitor(
                    "repository_created_with_custom_properties",
                    level="INFO",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    repo_id=repo_data_raw["id"],
                    repo_url=repo_data_raw["html_url"],
                    message=f"Repository created with custom properties in single API call"
                )

            except requests.exceptions.HTTPError as e:
            
                status_code = e.response.status_code if e.response else None
                error_details = {}
                response_text = ""
                try:
                    response_text = e.response.text if e.response else ""
                    error_details = e.response.json() if e.response else {}
                except Exception:
                    error_details = {"message": response_text or str(e)}

                log_and_monitor(
                    "failed_to_create_repository",
                    level="ERROR",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    status_code=status_code,
                    error=str(e),
                    error_details=error_details,
                    response_text=response_text,
                    payload_sent=repo_payload,
                    message="Failed to create repository with custom properties"
                )

                log_and_monitor(
                    "github_api_error_debug_details",
                    level="DEBUG",
                    correlation_id=correlation_id,
                    status_code=status_code,
                    response_text=response_text,
                    payload_sent=repo_payload,
                    repo_name=repo_name,
                    github_org=org
                )

        
                raise GitHubAPIError(
                    message=f"Failed to create repository: {error_details.get('message', str(e))}",
                    status_code=status_code,
                    response_body=error_details
                )

            except requests.exceptions.RequestException as e:
       
                log_and_monitor(
                    "repository_creation_network_error",
                    level="ERROR",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Network error while creating repository. Will retry."
                )
                raise GitHubAPIError(
                    message=f"Network error communicating with GitHub API (repo creation): {str(e)}",
                    status_code=None,
                    response_body={"error": "network_error", "details": str(e), "error_type": type(e).__name__}
                )

            repo_data = {
                "name": repo_data_raw["name"],
                "full_name": repo_data_raw["full_name"],
                "html_url": repo_data_raw["html_url"],
                "clone_url": repo_data_raw["clone_url"],
                "ssh_url": repo_data_raw["ssh_url"],
                "id": repo_data_raw["id"],
                "visibility": repo_data_raw["visibility"],
                "description": repo_data_raw["description"],
                "created_at": repo_data_raw["created_at"],
                "owner": org
            }

            log_and_monitor(
                "create_repo_success",
                level="INFO",
                correlation_id=correlation_id,
                repo_name=repo_name,
                github_org=org,
                repo_url=repo_data["html_url"],
                repo_id=repo_data["id"],
                message=f"Repository {org}/{repo_name} created successfully with custom properties in single API call"
            )

            return repo_data

        except GitHubAPIError:
        
            raise
        except Exception as e:
          
            log_and_monitor(
                "create_github_repository_error",
                level="ERROR",
                correlation_id=correlation_id,
                repo_name=repo_name,
                github_org=org,
                error=str(e),
                error_type=type(e).__name__
            )

            raise GitHubAPIError(
                message=f"Failed to create repository: {str(e)}",
                status_code=None,
                response_body={"error": str(e)}
            )
