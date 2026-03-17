"""Path validation utilities for workspace and plan workspace APIs."""

from fastapi import HTTPException, status


def validate_path(path: str) -> str:
    """Validate and normalize path. Raises ValueError for invalid paths (e.g. traversal)."""
    path = path.strip().lstrip("/")
    if ".." in path:
        raise ValueError("Invalid path: contains ..")
    return path


def validate_path_for_api(path: str) -> str:
    """Validate path for API handlers; raises HTTPException on invalid."""
    try:
        return validate_path(path)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
