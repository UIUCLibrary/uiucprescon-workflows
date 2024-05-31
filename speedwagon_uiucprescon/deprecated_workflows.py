"""Deprecated Workflows.

This contains all the workflows that are deprecated and ready for removal.
"""
from typing import Dict, Type, Any
import speedwagon
from .plugin import deprecated_workflows


@speedwagon.hookimpl
def registered_workflows() -> Dict[str, Type[speedwagon.Workflow[Any]]]:
    """Register workflows as part of the plugin."""
    return {
        workflow.name or str(workflow): workflow
        for workflow in deprecated_workflows
    }
