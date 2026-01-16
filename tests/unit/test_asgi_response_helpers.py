"""Tests for ASGI response helper functions.

This module tests the internal helper functions for sending ASGI HTTP responses,
including headers and body encoding.
"""

from __future__ import annotations

import pytest

from observabilipy.adapters.frameworks.asgi import _send_response


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.SendResponse.Headers")
@pytest.mark.asyncio
async def test_send_response_sends_correct_headers(asgi_send_capture):
    """_send_response sends http.response.start with correct status."""

    # Arrange: Get send capture fixture
    send, responses = asgi_send_capture

    # Act: Send response with specific status and content type
    await _send_response(send, 201, "text/plain", "test body")

    # Assert: Should send http.response.start with correct headers
    assert len(responses) == 2
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 201
    assert responses[0]["headers"] == [(b"content-type", b"text/plain")]


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.SendResponse.Body")
@pytest.mark.asyncio
async def test_send_response_sends_body_as_bytes(asgi_send_capture):
    """_send_response should send http.response.body with body encoded as bytes."""

    # Arrange: Get send capture fixture
    send, responses = asgi_send_capture

    # Act: Send response with string body
    await _send_response(send, 200, "application/json", "{'key': 'value'}")

    # Assert: Should send http.response.body with encoded body
    assert len(responses) == 2
    assert responses[1]["type"] == "http.response.body"
    assert responses[1]["body"] == b"{'key': 'value'}"
