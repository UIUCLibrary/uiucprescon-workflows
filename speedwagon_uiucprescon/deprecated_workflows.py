"""Deprecated Workflows.

This contains all the workflows that are deprecated and ready for removal.
"""

import speedwagon
from .plugin import deprecated_workflows


@speedwagon.hookimpl
def registered_workflows():
    return {workflow.name: workflow for workflow in deprecated_workflows}
