"""
Unit tests for JIRA client functionality.

Tests cover:
- JiraClient initialization
- Success comment building
- Failure comment building
- update_jira_success() function
- update_jira_failure() function
- transition_ticket_on_success() function
- Error handling and exception wrapping
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from jira.exceptions import JIRAError

from src.integrations.jira.client import (
    JiraClient,
    update_jira_success,
    update_jira_failure,
    update_jira_already_exists,
    transition_ticket_on_success,
    _build_success_comment,
    _build_failure_comment,
    _build_already_exists_comment,
)
from src.shared.exceptions import JiraAPIError


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_jira_client():
    """Mock JIRA client instance."""
    with patch('src.integrations.jira.client.JIRA') as mock_jira:
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance
        
        # Mock myself() for authentication
        mock_instance.myself.return_value = {'accountId': 'test-account-id'}
        
        yield mock_instance


@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch('src.integrations.jira.client.get_settings') as mock_get_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.jira_url = "https://test.atlassian.net"
        mock_settings_obj.jira_email = "hiya.modi.here@gmail.com"
        mock_settings_obj.jira_api_token = "test-token"
        mock_settings_obj.jira_api_timeout = 30
        mock_settings_obj.auto_transition_on_success = True
        mock_settings_obj.success_transition_name = "Done"
        mock_settings_obj.success_resolution = "Done"
        
        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj


@pytest.fixture
def sample_repo_data():
    """Sample repository data from GitHub."""
    return {
        "name": "test-repo",
        "full_name": "test-org/test-repo",
        "html_url": "https://github.com/test-org/test-repo",
        "clone_url": "https://github.com/test-org/test-repo.git",
        "ssh_url": "git@github.com:test-org/test-repo.git",
        "id": 123456,
        "private": True,
        "owner": "test-org",
        "created_at": "2024-01-01T00:00:00Z",
        "description": "Test repository"
    }


# ==============================================================================
# Test JiraClient Initialization
# ==============================================================================

class TestJiraClientInitialization:
    """Test JiraClient initialization and authentication."""
    
    def test_init_with_default_credentials(self, mock_jira_client, mock_settings):
        """Test initialization with credentials from settings."""
        client = JiraClient()
        
        assert client.jira_url == "https://test.atlassian.net"
        assert client.email == "hiya.modi.here@gmail.com"
        assert client.api_token == "test-token"
        assert client.timeout == 30
    
    def test_init_with_custom_credentials(self, mock_jira_client):
        """Test initialization with custom credentials."""
        client = JiraClient(
            jira_url="https://custom.atlassian.net",
            email="custom@example.com",
            api_token="custom-token"
        )
        
        assert client.jira_url == "https://custom.atlassian.net"
        assert client.email == "custom@example.com"
        assert client.api_token == "custom-token"
    
    def test_init_authentication_failure(self, mock_settings):
        """Test initialization fails when authentication fails."""
        with patch('src.integrations.jira.client.JIRA') as mock_jira:
            mock_jira.return_value.myself.side_effect = Exception("Authentication failed")
            
            with pytest.raises(JiraAPIError) as exc_info:
                JiraClient()
            
            assert "Failed to authenticate with JIRA" in str(exc_info.value)


# ==============================================================================
# Test Comment Building
# ==============================================================================

class TestCommentBuilding:
    """Test success and failure comment formatting."""
    
    def test_build_success_comment(self, sample_repo_data):
        """Test success comment formatting."""
        comment = _build_success_comment(sample_repo_data)

        assert "✅" in comment
        assert "Repository Created Successfully" in comment
        assert sample_repo_data["name"] in comment
        assert sample_repo_data["html_url"] in comment
        assert sample_repo_data["clone_url"] in comment
        assert sample_repo_data["ssh_url"] in comment
        assert sample_repo_data["owner"] in comment
        assert "Next Steps" in comment

    def test_build_failure_comment(self):
        """Test failure comment formatting."""
        error_msg = "Repository name already exists"
        comment = _build_failure_comment(error_msg)

        assert "❌" in comment
        assert "Repository Creation Failed" in comment
        assert error_msg in comment
        assert "Troubleshooting Steps" in comment
        assert "hiya.modi.here@gmail.com" in comment


# ==============================================================================
# Test update_jira_success
# ==============================================================================

class TestUpdateJiraSuccess:
    """Test update_jira_success function."""

    def test_success_update_adds_comment_and_labels(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test successful JIRA ticket update adds comment and labels."""
        # Mock issue for label update
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["existing-label"]
        mock_jira_client.issue.return_value = mock_issue

        # Mock transitions for transition_ticket_on_success
        mock_jira_client.transitions.return_value = [
            {"id": "31", "name": "Done"}
        ]

        result = update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert result is True

        # Verify comment was added
        mock_jira_client.add_comment.assert_called_once()
        comment_text = mock_jira_client.add_comment.call_args[0][1]
        assert "Repository Created Successfully" in comment_text

        # Verify labels were updated
        mock_issue.update.assert_called_once()
        labels_arg = mock_issue.update.call_args[1]["fields"]["labels"]
        assert "repository-created" in labels_arg
        assert "automated" in labels_arg
        assert "existing-label" in labels_arg

    def test_success_update_continues_on_label_failure(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test that label update failure doesn't fail the entire operation."""
        # Mock issue to raise exception on update
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        mock_issue.update.side_effect = Exception("Permission denied")
        mock_jira_client.issue.return_value = mock_issue

        # Mock transitions
        mock_jira_client.transitions.return_value = [
            {"id": "31", "name": "Done"}
        ]

        # Should still succeed despite label failure
        result = update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert result is True
        mock_jira_client.add_comment.assert_called_once()

    def test_success_update_handles_jira_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of JIRA API errors."""
        # Mock JIRA error
        jira_error = JIRAError(status_code=403, text="Permission denied")
        mock_jira_client.add_comment.side_effect = jira_error

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert exc_info.value.status_code == 403
        assert "permission denied" in str(exc_info.value).lower()

    def test_success_update_handles_unexpected_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of unexpected errors."""
        mock_jira_client.add_comment.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert "Unexpected error" in str(exc_info.value)


# ==============================================================================
# Test update_jira_already_exists
# ==============================================================================

class TestUpdateJiraAlreadyExists:
    """Test update_jira_already_exists function."""

    def test_already_exists_update_adds_comment_and_labels(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test update when repository already exists adds appropriate comment and labels."""
        # Mock issue for label update
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["existing-label"]
        mock_jira_client.issue.return_value = mock_issue

        # Mock transitions (though we won't use them for already-exists)
        mock_jira_client.transitions.return_value = []

        result = update_jira_already_exists("TEST-123", sample_repo_data, "corr-123")

        assert result is True

        # Verify comment was added
        mock_jira_client.add_comment.assert_called_once()
        comment_text = mock_jira_client.add_comment.call_args[0][1]
        assert "Repository Already Exists" in comment_text
        assert "idempotent" in comment_text.lower()

        # Verify labels were updated (different from creation)
        mock_issue.update.assert_called_once()
        labels_arg = mock_issue.update.call_args[1]["fields"]["labels"]
        assert "repository-already-exists" in labels_arg
        assert "automated" in labels_arg
        assert "existing-label" in labels_arg

    def test_already_exists_comment_format(self, sample_repo_data):
        """Test that already exists comment has correct format."""
        comment = _build_already_exists_comment(sample_repo_data)

        # Check key elements are present
        assert "Repository Already Exists" in comment
        assert "idempotent" in comment.lower()
        assert sample_repo_data['name'] in comment
        assert sample_repo_data['html_url'] in comment
        assert "What This Means" in comment
        assert "Next Steps" in comment

    def test_already_exists_continues_on_label_failure(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test that label update failure doesn't fail the entire operation."""
        # Mock issue to raise exception on update
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        mock_issue.update.side_effect = Exception("Permission denied")
        mock_jira_client.issue.return_value = mock_issue

        # Should still succeed despite label failure
        result = update_jira_already_exists("TEST-123", sample_repo_data, "corr-123")

        assert result is True
        mock_jira_client.add_comment.assert_called_once()

    def test_already_exists_handles_jira_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of JIRA API errors."""
        jira_error = JIRAError(status_code=403, text="Permission denied")
        mock_jira_client.add_comment.side_effect = jira_error

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_already_exists("TEST-123", sample_repo_data, "corr-123")

        assert exc_info.value.status_code == 403
        assert "permission denied" in str(exc_info.value).lower()


# ==============================================================================
# Test update_jira_failure
# ==============================================================================

class TestUpdateJiraFailure:
    """Test update_jira_failure function."""

    def test_failure_update_adds_comment_and_labels(self, mock_jira_client, mock_settings):
        """Test failure update adds comment and labels."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        mock_jira_client.issue.return_value = mock_issue

        result = update_jira_failure("TEST-123", "Repository creation failed", "corr-123")

        assert result is True

        # Verify comment was added
        mock_jira_client.add_comment.assert_called_once()
        comment_text = mock_jira_client.add_comment.call_args[0][1]
        assert "Repository Creation Failed" in comment_text
        assert "Repository creation failed" in comment_text

        # Verify labels were updated
        mock_issue.update.assert_called_once()
        labels_arg = mock_issue.update.call_args[1]["fields"]["labels"]
        assert "repository-creation-failed" in labels_arg
        assert "automated" in labels_arg

    def test_failure_update_best_effort_on_error(self, mock_jira_client, mock_settings):
        """Test failure update returns False on error (best-effort)."""
        mock_jira_client.add_comment.side_effect = Exception("JIRA error")

        # Should return False but not raise exception
        result = update_jira_failure("TEST-123", "Error message", "corr-123")

        assert result is False


# ==============================================================================
# Test transition_ticket_on_success
# ==============================================================================

class TestTransitionTicketOnSuccess:
    """Test ticket transition functionality."""

    def test_transition_when_enabled(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test ticket transitions to Done when enabled."""
        mock_settings.auto_transition_on_success = True

        # Mock available transitions
        mock_jira_client.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
            {"id": "41", "name": "Rejected"}
        ]

        result = transition_ticket_on_success("TEST-123", sample_repo_data, "corr-123")

        assert result is True

        # Verify transition was called with correct ID
        mock_jira_client.transition_issue.assert_called_once()
        call_args = mock_jira_client.transition_issue.call_args
        assert call_args[0][0] == "TEST-123"  # ticket_id
        assert call_args[0][1] == "31"  # transition_id for "Done"

    def test_transition_when_disabled(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test transition is skipped when disabled."""
        mock_settings.auto_transition_on_success = False

        result = transition_ticket_on_success("TEST-123", sample_repo_data, "corr-123")

        assert result is False
        mock_jira_client.transitions.assert_not_called()
        mock_jira_client.transition_issue.assert_not_called()

    def test_transition_not_found(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test when target transition is not available."""
        mock_settings.auto_transition_on_success = True
        mock_settings.success_transition_name = "Done"

        # Mock transitions without "Done"
        mock_jira_client.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "41", "name": "Rejected"}
        ]

        result = transition_ticket_on_success("TEST-123", sample_repo_data, "corr-123")

        assert result is False
        mock_jira_client.transition_issue.assert_not_called()

    def test_transition_with_resolution(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test transition includes resolution field when configured."""
        mock_settings.auto_transition_on_success = True
        mock_settings.success_resolution = "Done"

        mock_jira_client.transitions.return_value = [
            {"id": "31", "name": "Done"}
        ]

        result = transition_ticket_on_success("TEST-123", sample_repo_data, "corr-123")

        assert result is True

        # Verify resolution was included in transition
        call_args = mock_jira_client.transition_issue.call_args
        fields = call_args[1]["fields"]
        assert fields is not None
        assert "resolution" in fields
        assert fields["resolution"]["name"] == "Done"

    def test_transition_best_effort_on_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test transition returns False on error (best-effort)."""
        mock_settings.auto_transition_on_success = True

        mock_jira_client.transitions.return_value = [{"id": "31", "name": "Done"}]
        mock_jira_client.transition_issue.side_effect = Exception("Transition error")

        # Should return False but not raise exception
        result = transition_ticket_on_success("TEST-123", sample_repo_data, "corr-123")

        assert result is False


# ==============================================================================
# Test Error Handling
# ==============================================================================

class TestErrorHandling:
    """Test exception handling and conversion."""

    def test_handle_jira_401_error(self, mock_jira_client):
        """Test handling of 401 authentication error."""
        with patch('src.integrations.jira.client.JIRA') as mock_jira_constructor:
            mock_jira_constructor.return_value.myself.side_effect = JIRAError(
                status_code=401,
                text="Authentication failed"
            )

            with pytest.raises(JiraAPIError) as exc_info:
                JiraClient()

            assert "Failed to authenticate" in str(exc_info.value)

    def test_handle_jira_403_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of 403 permission denied error."""
        jira_error = JIRAError(status_code=403, text="Permission denied")
        jira_error.response = Mock()
        jira_error.response.json.return_value = {"errorMessages": ["No permission"]}

        mock_jira_client.add_comment.side_effect = jira_error

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert exc_info.value.status_code == 403
        assert "permission" in str(exc_info.value).lower()

    def test_handle_jira_404_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of 404 ticket not found error."""
        jira_error = JIRAError(status_code=404, text="Issue not found")
        mock_jira_client.add_comment.side_effect = jira_error

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_success("TEST-123", sample_repo_data, "corr-123")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value).lower()

    def test_handle_network_error(self, mock_jira_client, mock_settings, sample_repo_data):
        """Test handling of network errors."""
        mock_jira_client.add_comment.side_effect = ConnectionError("Network timeout")

        with pytest.raises(JiraAPIError) as exc_info:
            update_jira_success("TEST-123", sample_repo_data, "corr-123")

        # Network errors should have status_code=None (retryable)
        assert exc_info.value.status_code is None
        assert "Unexpected error" in str(exc_info.value)

