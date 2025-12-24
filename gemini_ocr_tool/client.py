"""Gemini client management for OCR operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import os

from google import genai
from google.genai import types


class GeminiClientError(Exception):
    """Base exception for Gemini client errors."""

    pass


class AuthenticationError(GeminiClientError):
    """Raised when authentication fails."""

    pass


def create_client(
    api_key: str | None = None,
    use_vertex: bool = False,
    project: str | None = None,
    location: str | None = None,
) -> genai.Client:
    """Create and configure a Gemini client for OCR operations.

    Supports both Gemini Developer API and Vertex AI authentication.
    Uses v1alpha API to access media_resolution feature for better OCR quality.

    Args:
        api_key: API key for Gemini Developer API (optional, reads from env)
        use_vertex: Whether to use Vertex AI instead of Developer API
        project: Google Cloud project ID (required for Vertex AI)
        location: Google Cloud location (required for Vertex AI)

    Returns:
        Configured Gemini client with v1alpha API

    Raises:
        AuthenticationError: If authentication configuration is invalid
    """
    # Vertex AI configuration
    use_vertex_env = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1", "yes")
    if use_vertex or use_vertex_env:
        if not project:
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not location:
            location = os.getenv("GOOGLE_CLOUD_LOCATION")

        if not project:
            raise AuthenticationError(
                "GOOGLE_CLOUD_PROJECT environment variable or --project is required for Vertex AI"
            )
        if not location:
            raise AuthenticationError(
                "GOOGLE_CLOUD_LOCATION environment variable or --location is required for Vertex AI"
            )
        try:
            return genai.Client(
                vertexai=True,
                project=project,
                location=location,
                http_options=types.HttpOptions(api_version="v1alpha"),
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to create Vertex AI client: {e}") from e

    # Gemini Developer API configuration
    # Priority: 1. Explicit api_key param, 2. GOOGLE_API_KEY, 3. GEMINI_API_KEY
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise AuthenticationError(
            "API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable. "
            "Get your API key from https://aistudio.google.com/app/apikey"
        )

    try:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1alpha"),
        )
    except Exception as e:
        raise AuthenticationError(f"Failed to create Gemini client: {e}") from e
