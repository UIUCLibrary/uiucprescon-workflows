"""Active Workflows."""

from typing import Dict, Type, Any
import speedwagon
from .plugin import active_workflows


@speedwagon.hookimpl
def registered_workflows() -> Dict[str, Type[speedwagon.Workflow[Any]]]:
    """Register workflows."""
    return {
        workflow.name or str(workflow): workflow
        for workflow in active_workflows
    }
