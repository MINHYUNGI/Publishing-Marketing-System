"""Compatibility entry point for older run.ps1 versions."""

from sns_content_consolidated_patch import apply_patch


if __name__ == "__main__":
    apply_patch()
