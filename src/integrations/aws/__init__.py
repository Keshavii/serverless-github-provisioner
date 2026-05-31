"""
AWS Service Integrations

Adapters for AWS services including Secrets Manager.
"""

from .secrets_manager import get_secret

__all__ = ['get_secret']
