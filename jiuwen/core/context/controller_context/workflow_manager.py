from typing import Dict, List

from jiuwen.core.utils.tool.base import Tool
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from jiuwen.core.workflow.base import Workflow


class WorkflowMgr:
    def __init__(self, agent_config):
        self._workflows: Dict[str, Workflow] = dict()
        self._tools: Dict[str, Tool] = dict()

    def get_workflow(self, workflow_instance_id: str) -> Workflow:
        return self._workflows.get(workflow_instance_id)

    def add_workflows(self, workflows: List[Workflow]):
        if not workflows:
            return
        for workflow in workflows:
            workflow_id = workflow.config().metadata.id
            workflow_version = workflow.config().metadata.version
            self._workflows.update({f"{workflow_id}_{workflow_version}": workflow})

    def find_workflow_by_id_and_version(self, workflow_id: str, workflow_version: str):
        return self._workflows.get(f"{workflow_id}_{workflow_version}")

    def add_tools(self, tools: List[Tool]):
        if not tools:
            return
        for tool in tools:
            if isinstance(tool, RestfulApi):
                tool_name = tool.name
                self._tools.update({tool_name: tool})

    def find_tool_by_name(self, tool_name: str):
        return self._tools.get(tool_name)
