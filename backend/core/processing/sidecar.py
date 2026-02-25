"""
JSON sidecar writer for processed documents.

Saves processed document metadata and text to JSON files alongside originals.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from backend.core.processing.schemas import ProcessedDocumentSchema

logger = logging.getLogger(__name__)


def generate_sidecar_path(original_path: Path) -> Path:
    """Generate the path for the JSON sidecar file.

    Args:
        original_path: Path to original document.

    Returns:
        Path for the JSON sidecar file.
    """
    return original_path.with_suffix(f"{original_path.suffix}_processed.json")


def save_json_sidecar(
    original_path: Path,
    processed_schema: ProcessedDocumentSchema,
) -> Path:
    """Save processed document as JSON sidecar.

    Args:
        original_path: Path to original document.
        processed_schema: Validated processing result.

    Returns:
        Path to saved JSON file.
    """
    sidecar_path = generate_sidecar_path(original_path)

    data = processed_schema.model_dump(mode="json")

    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved JSON sidecar: {sidecar_path}")

    return sidecar_path


def load_json_sidecar(sidecar_path: Path) -> ProcessedDocumentSchema:
    """Load processed document from JSON sidecar.

    Args:
        sidecar_path: Path to JSON sidecar file.

    Returns:
        Validated ProcessedDocumentSchema.
    """
    with open(sidecar_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return ProcessedDocumentSchema(**data)


def sidecar_exists(original_path: Path) -> bool:
    """Check if JSON sidecar exists for a document.

    Args:
        original_path: Path to original document.

    Returns:
        True if sidecar exists.
    """
    return generate_sidecar_path(original_path).exists()


def delete_sidecar(original_path: Path) -> bool:
    """Delete JSON sidecar for a document.

    Args:
        original_path: Path to original document.

    Returns:
        True if deleted, False if didn't exist.
    """
    sidecar_path = generate_sidecar_path(original_path)
    if sidecar_path.exists():
        sidecar_path.unlink()
        logger.info(f"Deleted sidecar: {sidecar_path}")
        return True
    return False
