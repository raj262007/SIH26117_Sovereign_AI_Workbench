"""
File management and audit utilities for Sovereign Agentic AI Workbench.
Handles safe path resolution, directory scaffolding, and SHA-256 forensic hashing.
"""

import os
import hashlib
from typing import Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
INPUTS_DIR = os.path.join(DATA_DIR, "sample_inputs")

def ensure_directories() -> None:
    """Ensure data and output directories exist."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(INPUTS_DIR, exist_ok=True)

def get_output_path(filename: str) -> str:
    """Resolve an absolute path inside the data/outputs directory."""
    ensure_directories()
    return os.path.join(OUTPUTS_DIR, filename)

def compute_sha256(content_or_filepath: str) -> str:
    """
    Compute the SHA-256 hash of a file or string.
    Provides forensic audit proof for generated deliverables.
    """
    hasher = hashlib.sha256()
    if os.path.isfile(content_or_filepath):
        with open(content_or_filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
    else:
        hasher.update(content_or_filepath.encode("utf-8"))
    return hasher.hexdigest()

def read_text_file(filepath: str) -> str:
    """Safely read and return text from a local file."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
