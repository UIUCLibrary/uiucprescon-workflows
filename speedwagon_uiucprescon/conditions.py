"""Conditions."""
from __future__ import annotations

import os
import typing

if typing.TYPE_CHECKING:
    import speedwagon.validators
    import speedwagon.workflow


def candidate_exists(
        candidate: speedwagon.validators.FilePath,
        _: speedwagon.workflow.UserData) -> bool:
    """Check if a candidate exists.

    Args:
        candidate: value to check
        _:

    Returns: True if exists, False if not

    """
    return os.path.exists(candidate)
