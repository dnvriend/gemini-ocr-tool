"""OCR processor using Gemini 3 Flash.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types

from gemini_ocr_tool.client import GeminiClientError
from gemini_ocr_tool.logging_config import get_logger

logger = get_logger(__name__)

# Model ID for Gemini 3 Flash (preview)
MODEL_ID = "gemini-3-flash-preview"
# Fallback to stable model if preview unavailable
MODEL_FALLBACK = "gemini-2.5-flash"

# Default OCR prompt
DEFAULT_PROMPT = (
    "Extract all text from this document. "
    "Maintain the layout using Markdown. "
    "If there are tables, format them as GitHub-flavored Markdown tables."
)

# Gemini 3 Flash pricing (per 1M tokens)
INPUT_COST_PER_1M_TOKENS = 0.50
OUTPUT_COST_PER_1M_TOKENS = 3.00


@dataclass
class OcrResult:
    """Result of OCR processing with token usage."""

    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


def extract_text_from_document(
    client: genai.Client,
    file_path: Path,
    prompt: str = DEFAULT_PROMPT,
) -> OcrResult:
    """Extract text from document using Gemini 3 Flash.

    Supports both images (PNG, JPG, JPEG) and PDFs.
    Returns text along with token usage for cost calculation.

    Args:
        client: Configured Gemini client
        file_path: Path to document file
        prompt: OCR instruction prompt

    Returns:
        OcrResult containing text and token usage

    Raises:
        FileNotFoundError: If file doesn't exist
        GeminiClientError: If OCR extraction fails
    """
    logger.debug("Extracting text from: %s", file_path)

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file contents
    file_bytes = file_path.read_bytes()
    file_size_mb = len(file_bytes) / 1024 / 1024
    logger.debug("File size: %.2f MB", file_size_mb)

    # Get MIME type
    mime_type = _get_mime_type(file_path)
    logger.debug("MIME type: %s", mime_type)

    # Configure generation with low thinking for speed
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    )

    # Build content parts
    contents = [
        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        prompt,
    ]

    logger.debug("Calling Gemini API with model: %s", MODEL_ID)

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config,
        )

        extracted_text = response.text
        if extracted_text is None:
            raise GeminiClientError(f"No text extracted from {file_path.name}")

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = (
            usage.prompt_token_count
            if usage is not None and usage.prompt_token_count is not None
            else 0
        )
        output_tokens = (
            usage.candidates_token_count
            if usage is not None and usage.candidates_token_count is not None
            else 0
        )
        total_tokens = (
            usage.total_token_count
            if usage is not None and usage.total_token_count is not None
            else 0
        )

        word_count = len(extracted_text.split())
        logger.debug(
            "Extracted %d words from %s (tokens: %d in, %d out, %d total)",
            word_count,
            file_path.name,
            input_tokens,
            output_tokens,
            total_tokens,
        )

        return OcrResult(
            text=extracted_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    except Exception as e:
        logger.error("OCR extraction failed for %s: %s", file_path.name, e)
        logger.debug("Full traceback:", exc_info=True)
        raise GeminiClientError(f"OCR extraction failed: {e}") from e


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M_TOKENS
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M_TOKENS
    return input_cost + output_cost


def _get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file.

    Args:
        file_path: Path to file

    Returns:
        MIME type string

    Raises:
        ValueError: If file type is not supported
    """
    suffix = file_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
    }
    if suffix not in mime_types:
        raise ValueError(f"Unsupported file type: {suffix}")
    return mime_types[suffix]
