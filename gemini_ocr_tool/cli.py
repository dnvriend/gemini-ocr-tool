"""CLI entry point for gemini-ocr-tool.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import os
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path

import click
from tqdm import tqdm

from gemini_ocr_tool.client import AuthenticationError, GeminiClientError, create_client
from gemini_ocr_tool.file_handler import discover_documents
from gemini_ocr_tool.logging_config import get_logger, setup_logging
from gemini_ocr_tool.ocr_processor import OcrResult, calculate_cost, extract_text_from_document

logger = get_logger(__name__)


@click.command()
@click.argument("glob_pattern")
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output (use -v for INFO, -vv for DEBUG, -vvv for TRACE)",
)
@click.option(
    "--max-workers",
    type=int,
    default=None,
    show_default=False,
    help="Maximum number of parallel OCR requests (default: number of CPU cores)",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="Gemini API key (default: reads from GEMINI_API_KEY or GOOGLE_API_KEY env var)",
)
@click.option(
    "--use-vertex",
    is_flag=True,
    default=False,
    help="Use Vertex AI instead of Gemini Developer API",
)
@click.option(
    "--project",
    type=str,
    default=None,
    help="Google Cloud project ID (required for Vertex AI)",
)
@click.option(
    "--location",
    type=str,
    default=None,
    help="Google Cloud location (required for Vertex AI)",
)
@click.version_option(version="0.1.0")
def main(
    glob_pattern: str,
    output_file: Path,
    verbose: int,
    max_workers: int | None,
    api_key: str | None,
    use_vertex: bool,
    project: str | None,
    location: str | None,
) -> None:
    """Extract text from documents using Gemini 3 Flash and create a markdown document.

    Processes images (PNG, JPG, JPEG) and PDFs in natural sort order
    and appends extracted text sequentially to create a coherent document.

    Uses parallel processing for faster batch processing while maintaining
    correct document order in the output.

    GLOB_PATTERN: Pattern to match document files (e.g., "*.png", "*.pdf", "dir/*.jpg")
    OUTPUT_FILE: Path to output markdown file (will be overwritten)

    \b
    Examples:

    \b
        # Process all PNG files in current directory
        gemini-ocr-tool "*.png" output.md

    \b
        # Process PDFs from subdirectory with 8 parallel workers
        gemini-ocr-tool "docs/*.pdf" chapter-3.md --max-workers=8

    \b
        # Process numbered files in order
        gemini-ocr-tool "001-*.png" notes.md

    \b
        # Enable verbose logging
        gemini-ocr-tool "*.png" output.md -v   # INFO level
        gemini-ocr-tool "*.png" output.md -vv  # DEBUG level
        gemini-ocr-tool "*.png" output.md -vvv # TRACE level

    \b
        # Use Vertex AI authentication
        gemini-ocr-tool "*.pdf" output.md --use-vertex --project=my-project --location=us-central1

    \b
    Output Format:
        Creates a single markdown file with:
        - Source comment for each document: <!-- Source: filename.png -->
        - Extracted text in markdown format (tables, headings, lists)
        - Horizontal rules (---) between documents

    \b
    Prerequisites:
        1. Get API key from https://aistudio.google.com/app/apikey
        2. Set environment variable: export GEMINI_API_KEY=your_key

    \b
    Troubleshooting:
        - "No files match pattern" → Check glob pattern and file paths
        - "API key is required" → Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable
        - "OCR extraction failed" → Check your API key quota and network connection
    """
    setup_logging(verbose)

    # Default to number of CPU cores if not specified
    if max_workers is None:
        max_workers = os.cpu_count() or 4

    try:
        # Create Gemini client
        logger.debug("Creating Gemini client")
        client = create_client(
            api_key=api_key,
            use_vertex=use_vertex,
            project=project,
            location=location,
        )

        # Discover and sort documents
        doc_paths = discover_documents(glob_pattern)
        logger.info("Found %d documents matching pattern: %s", len(doc_paths), glob_pattern)

        click.echo(f"Found {len(doc_paths)} documents to process")
        click.echo(f"Processing with {max_workers} parallel workers...")

        # Submit all tasks, tagging each future with its index for ordering
        future_to_index: dict[Future[OcrResult], tuple[int, Path]] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, doc_path in enumerate(doc_paths):
                future = executor.submit(extract_text_from_document, client, doc_path)
                future_to_index[future] = (idx, doc_path)
                logger.debug("Submitted task %d: %s", idx + 1, doc_path.name)

            # Collect results as they complete, with progress bar
            results: list[tuple[int, Path, OcrResult]] = []
            failed: list[tuple[int, Path, str]] = []

            for future in tqdm(
                as_completed(future_to_index.keys()),
                total=len(future_to_index),
                desc="Processing documents",
                unit="doc",
            ):
                idx, doc_path = future_to_index[future]
                try:
                    ocr_result: OcrResult = future.result()
                    results.append((idx, doc_path, ocr_result))
                    logger.info(
                        "Completed %d/%d: %s (%d tokens)",
                        idx + 1,
                        len(doc_paths),
                        doc_path.name,
                        ocr_result.total_tokens,
                    )
                except Exception as e:
                    error_msg = f"[ERROR: Failed to process {doc_path.name}: {e}]"
                    failed.append((idx, doc_path, error_msg))
                    logger.error("Failed to process %s: %s", doc_path.name, e)

        # Sort results by original index to maintain order
        results.sort(key=lambda x: x[0])
        failed.sort(key=lambda x: x[0])

        # Aggregate token usage
        total_input_tokens = sum(r[2].input_tokens for r in results)
        total_output_tokens = sum(r[2].output_tokens for r in results)
        total_tokens = sum(r[2].total_tokens for r in results)
        total_cost = calculate_cost(total_input_tokens, total_output_tokens)

        # Write all results to output file in correct order
        with output_file.open("w") as f:
            for idx, doc_path, ocr_result in results:
                if idx > 0:
                    f.write("\n\n---\n\n")
                f.write(f"<!-- Source: {doc_path.name} -->\n\n")
                f.write(ocr_result.text)

            # Write any failures at the end
            if failed:
                f.write("\n\n---\n\n")
                f.write("## Failed Documents\n\n")
                for _, doc_path, error_msg in failed:
                    f.write(f"{error_msg}\n\n")

        # Display results
        successful = len(results)
        total = len(doc_paths)
        click.echo(f"\n✓ Successfully processed {successful}/{total} documents")
        if failed:
            click.echo(f"✗ {len(failed)} documents failed (see errors in output)")

        # Display cost breakdown
        click.echo(f"\n{'─' * 40}")
        click.echo("Token Usage & Cost")
        click.echo(f"{'─' * 40}")
        click.echo(f"  Input tokens:  {total_input_tokens:,}")
        click.echo(f"  Output tokens: {total_output_tokens:,}")
        click.echo(f"  Total tokens:  {total_tokens:,}")
        click.echo(f"\n  Estimated cost: ${total_cost:.4f} USD")
        click.echo(f"{'─' * 40}")
        click.echo("  Pricing: $0.50/1M input, $3.00/1M output")
        click.echo(f"✓ Output written to: {output_file}")

    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()
    except AuthenticationError as e:
        click.echo(f"✗ Authentication Error: {e}", err=True)
        click.echo("\nGet your API key from: https://aistudio.google.com/app/apikey", err=True)
        raise click.Abort()
    except GeminiClientError as e:
        click.echo(f"✗ Error: {e}", err=True)
        click.echo("\nTroubleshooting:", err=True)
        click.echo("  - Verify your API key is valid", err=True)
        click.echo("  - Check your API quota at https://aistudio.google.com/app/apikey", err=True)
        click.echo("  - Ensure you have network connectivity", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
