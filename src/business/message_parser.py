"""
SQS Message Parser and Sanitizer

Handles parsing and sanitization of SQS messages originating from JIRA Automation.
Addresses common data quality issues including URL encoding, extraneous whitespace,
and control characters that can interfere with downstream processing.
"""

import json
import re
from typing import Dict
from urllib.parse import unquote_plus

from ..observability import log_and_monitor


def parse_sqs_message(record: Dict, correlation_id: str) -> Dict:
    """
    Parse and sanitize SQS message from JIRA Automation.

    Handles multiple message formats and data quality issues commonly encountered
    with JIRA Automation webhooks, including URL encoding, JSON with embedded
    spaces, and control characters.

    Args:
        record: SQS record containing messageId, body, and metadata
        correlation_id: Unique identifier for request tracing and log correlation

    Returns:
        Sanitized message body as dictionary with validated JSON structure

    Raises:
        json.JSONDecodeError: If message body cannot be parsed as valid JSON
                             after attempting all sanitization strategies

    Message Format Handling:
        - URL-encoded bodies (Content-Type: application/x-www-form-urlencoded)
        - Plain JSON with JIRA-inserted whitespace
        - JSON with control characters and special characters
    """
    message_id = record['messageId']
    raw_body = record['body']

    if raw_body.startswith('%'):
        return _parse_url_encoded_body(raw_body, message_id, correlation_id)
    else:
        return _parse_json_body(raw_body, message_id, correlation_id)


def _parse_url_encoded_body(raw_body: str, message_id: str, correlation_id: str) -> Dict:
    """
    Parse URL-encoded body from JIRA Automation.
    
    JIRA Automation sends URL-encoded JSON with extra spaces.
    This function:
    1. URL decodes the body
    2. Removes JIRA-added spaces
    3. Sanitizes control characters if needed
    """
    decoded_body = unquote_plus(raw_body)

    print(f"🔍 Decoded body (first 200 chars): {decoded_body[:200]}")

    decoded_body = _clean_jira_spaces(decoded_body)

    print(f"🔍 Cleaned body (first 200 chars): {decoded_body[:200]}")

    try:
        return json.loads(decoded_body)
    except json.JSONDecodeError as e:
        log_and_monitor(
            "json_parse_error_url_decoded_path",
            level="WARNING",
            correlation_id=correlation_id,
            message_id=message_id,
            error=str(e)
        )
        sanitized_body = _sanitize_control_characters(decoded_body)
        return json.loads(sanitized_body)


def _parse_json_body(raw_body: str, message_id: str, correlation_id: str) -> Dict:
    """
    Parse regular JSON body from webhook handler.
    
    Attempts to parse JSON, and if it fails, sanitizes control characters and retries.
    """
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as e:
        log_and_monitor(
            "json_parse_error_attempting_fix",
            level="WARNING",
            correlation_id=correlation_id,
            message_id=message_id,
            error=str(e),
            char_position=e.pos if hasattr(e, 'pos') else None
        )

        sanitized_body = _sanitize_control_characters(raw_body)

        try:
            message_body = json.loads(sanitized_body)
            log_and_monitor(
                "json_parse_recovered",
                level="INFO",
                correlation_id=correlation_id,
                message_id=message_id,
                message="Successfully parsed JSON after sanitizing control characters"
            )
            return message_body
        except json.JSONDecodeError as e2:
            log_and_monitor(
                "json_parse_failed_after_sanitization",
                level="ERROR",
                correlation_id=correlation_id,
                message_id=message_id,
                error=str(e2),
                raw_body_sample=raw_body[:500]
            )
            raise


def _clean_jira_spaces(body: str) -> str:
    """
    Remove extra spaces that JIRA Automation adds to JSON structure.
    
    Removes spaces after { [ , : and before } ] ,
    """
    body = re.sub(r'([\{\[])\s+', r'\1', body)
    body = re.sub(r'\s+([\}\]])', r'\1', body)
    body = re.sub(r'"\s*:\s*', '":', body)
    body = re.sub(r'\s*,\s*', ',', body)
    return body


def _sanitize_control_characters(body: str) -> str:
    """
    Sanitize control characters that break JSON parsing.
    
    Escapes: newline, carriage return, tab, backspace, form feed
    Removes: other unprintable control characters
    """
    body = (body
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t')
        .replace('\b', '\\b')
        .replace('\f', '\\f')
    )

    body = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', body)

    return body
