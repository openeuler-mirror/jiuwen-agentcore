from typing import List

from pydantic import Field

from jiuwen.agent.config.base import AgentConfig
from jiuwen.agent.controller.base import Controller, ControllerOutput, ControllerInput
from jiuwen.core.agent.task.task import SubTask


class WorkflowControllerOutput(ControllerOutput):
    sub_tasks: List[SubTask] = Field(default_factory=list)


class WorkflowControllerInput(ControllerInput):
    ...


class WorkflowController(Controller):
    """
    根据输入生成 WorkflowControllerOutput
    """

    def __init__(self, config: AgentConfig, context_mgr):
        super().__init__(config, context_mgr)

    def invoke(self, inputs: WorkflowControllerInput) -> WorkflowControllerOutput:
        return WorkflowControllerOutput()
