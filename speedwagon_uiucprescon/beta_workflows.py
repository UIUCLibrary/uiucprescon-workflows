"""Active Workflows."""

from typing import Dict, Type, Any
import speedwagon
from . import workflow_make_pdf


@speedwagon.hookimpl
def registered_workflows() -> Dict[str, Type[speedwagon.Workflow[Any]]]:
    """Register workflows."""
    return {
        "Make PDF Book": workflow_make_pdf.MakePDFWorkflow
    }
