"""Legacy compatibility shim.

SNS performance rendering is now handled only by sns_content_consolidated_patch.py.
This file intentionally performs no UI mutation so older run.ps1 versions remain safe.
"""


def apply_patch() -> None:
    return


if __name__ == "__main__":
    apply_patch()
