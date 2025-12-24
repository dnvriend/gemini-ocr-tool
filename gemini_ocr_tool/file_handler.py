"""File discovery and sorting utilities.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import re
from pathlib import Path

from gemini_ocr_tool.logging_config import get_logger

logger = get_logger(__name__)


def natural_sort_key(path: Path) -> tuple[float, str]:
    """Generate sort key for natural sorting.

    Extracts numeric portions from filename for natural ordering.
    Examples:
        IMG_4169.png -> (4169, "IMG_4169.png")
        001-intro.png -> (1, "001-intro.png")
        chapter-10.png -> (10, "chapter-10.png")

    Args:
        path: Path to file

    Returns:
        Tuple of (first_number_found, filename) for sorting
    """
    filename = path.name
    numbers = re.findall(r"\d+", filename)
    if numbers:
        return (float(numbers[0]), filename)
    return (float("inf"), filename)


def discover_documents(glob_pattern: str) -> list[Path]:
    """Discover and sort document files matching glob pattern.

    Supports images (PNG, JPG, JPEG) and PDFs.
    Supports recursive glob with ** (e.g., "**/*.png" for all subdirectories).

    Args:
        glob_pattern: Glob pattern (e.g., "*.png", "**/*.pdf", "docs/*.jpg")

    Returns:
        Sorted list of Path objects

    Raises:
        ValueError: If no files match pattern
    """
    logger.debug("Discovering documents with pattern: %s", glob_pattern)

    # Determine if pattern is absolute or relative
    pattern_path = Path(glob_pattern)
    is_absolute = pattern_path.is_absolute()

    # For absolute patterns, use root as base directory
    # For relative patterns, use current directory
    if is_absolute:
        # Get the anchor (root + parts up to first wildcard)
        base = _find_base_directory(pattern_path)
        pattern = str(pattern_path)
    else:
        base = Path.cwd()
        pattern = glob_pattern

    logger.debug("Base directory: %s, pattern: %s", base, pattern)

    # Check if pattern uses recursive glob
    recursive = "**" in pattern

    # Find matches using glob
    try:
        if recursive:
            # Use rglob for recursive patterns - extract the pattern after **
            if "**/" in pattern:
                # Pattern like "**/*.png" or "dir/**/*.png"
                parts = pattern.split("**/", 1)
                if parts[0]:
                    base = base / parts[0]
                glob_suffix = parts[1] if len(parts) > 1 else "*"
            else:
                glob_suffix = "*"

            matches = list(base.rglob(glob_suffix))
        else:
            # Simple glob pattern
            matches = list(base.glob(pattern))
    except Exception as e:
        logger.error("Glob pattern failed: %s", e)
        raise ValueError(f"Invalid glob pattern: {glob_pattern}") from e

    logger.debug("Found %d total matches", len(matches))

    if not matches:
        logger.error("No files match pattern: %s", glob_pattern)
        raise ValueError(f"No files match pattern: {glob_pattern}")

    # Filter for supported extensions
    supported_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".pdf",
        ".PNG",
        ".JPG",
        ".JPEG",
        ".PDF",
    }
    paths = [p for p in matches if p.suffix in supported_extensions and p.is_file()]
    logger.debug("Filtered to %d document files", len(paths))

    if not paths:
        logger.error("No supported documents found matching: %s", glob_pattern)
        raise ValueError(f"No supported documents found matching: {glob_pattern}")

    # Sort naturally
    paths.sort(key=natural_sort_key)
    logger.debug("Sorted %d documents naturally", len(paths))

    if logger.isEnabledFor(10):  # DEBUG level
        for idx, path in enumerate(paths[:5], 1):
            logger.debug("  %d. %s", idx, path.name)
        if len(paths) > 5:
            logger.debug("  ... and %d more", len(paths) - 5)

    return paths


def _find_base_directory(pattern_path: Path) -> Path:
    """Find the base directory for an absolute glob pattern.

    For patterns like /absolute/path/**/*.png, returns /absolute/path.
    For patterns like /absolute/path/*.png, returns /absolute/path.

    Args:
        pattern_path: Absolute Path object with glob pattern

    Returns:
        Base directory Path
    """
    # Build the base path from parts until we hit a wildcard
    parts = []
    root = pattern_path.anchor if pattern_path.anchor else ""

    for part in pattern_path.parts:
        if "*" in part or "?" in part or "[" in part:
            break
        parts.append(part)

    return Path(root + "/".join(parts)) if root else Path("/".join(parts))


def get_mime_type(file_path: Path) -> str:
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
