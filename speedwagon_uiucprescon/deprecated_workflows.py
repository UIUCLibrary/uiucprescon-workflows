"""Deprecated Workflows.

This contains all the workflows that are deprecated and ready for removal.
"""

import speedwagon
from .plugin import deprecated_workflows


@speedwagon.hookimpl
def registered_workflows():
    """Register workflows as part of the plugin."""
    return {workflow.name: workflow for workflow in deprecated_workflows}
