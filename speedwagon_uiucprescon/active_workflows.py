import speedwagon
from .plugin import active_workflows


@speedwagon.hookimpl
def registered_workflows():
    return {workflow.name: workflow for workflow in active_workflows}
