import speedwagon
from .plugin import deprecated_workflows
@speedwagon.hookimpl
def registered_workflows():
    return {workflow.name: workflow for workflow in deprecated_workflows}