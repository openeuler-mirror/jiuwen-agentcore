from typing import Dict, List

from jiuwen.core.workflow.base import Workflow


class WorkflowMgr:
    def __init__(self):
        self._workflows: Dict[str, Workflow] = dict()

    def add_workflows(self, workflows: List[Workflow]):
        if not workflows:
            return
        for workflow in workflows:
            workflow_id = workflow.config().metadata.id
            workflow_version = workflow.config().metadata.version
            self._workflows.update({f"{workflow_id}_{workflow_version}": workflow})
