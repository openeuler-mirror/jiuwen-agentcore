from typing import Dict

from jiuwen.agent.config.workflow_config import WorkflowAgentConfig
from jiuwen.core.context.controller_context.controller_context_manager import ControllerContextMgr
from jiuwen.core.agent.controller.workflow_controller import WorkflowController, WorkflowControllerOutput
from jiuwen.core.agent.agent import Agent
from jiuwen.core.agent.handler.base import AgentHandlerImpl
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState


class WorkflowAgent(Agent):
    def __init__(self, agent_config: WorkflowAgentConfig):
        super().__init__(agent_config)

    def _init_controller(self):
        return WorkflowController(self._config, self._controller_context_manager)

    def _init_agent_handler(self):
        return AgentHandlerImpl()

    def _init_controller_context_manager(self) -> ControllerContextMgr:
        context = Context(config=Config(), state=InMemoryState(), store=None, tracer=None)
        return ControllerContextMgr(self._config, context)

    def _init_task_manager(self):
        return None

    def invoke(self, inputs: Dict, context: Context) -> Dict:
        output: WorkflowControllerOutput = self._controller.invoke(inputs)

        outputs = [self._agent_handler.invoke(st) for st in output.sub_tasks]

        return {"outputs": outputs}

    def stream(self, inputs: Dict, context: Context):
        pass
