from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional, Dict, List

from jiuwen.agent.config.base import AgentConfig
from jiuwen.agent.context.controller_context_manager import ControllerContextMgr
from jiuwen.core.context.context import Context
from jiuwen.core.workflow.base import Workflow


class Agent(ABC):
    """
    最顶层抽象，所有 Agent 的公共基类。
    子类必须实现：
        - invoke : 同步一次性调用
        - stream : 流式调用
    """

    def __init__(self, agent_config: "AgentConfig"):
        self._config = agent_config
        self._controller_context_manager: Optional["ControllerContextMgr"] = \
            self._init_controller_context_manager()
        self._controller: "Controller | None" = self._init_controller()
        self._agent_handler: "AgentHandler | None" = self._init_agent_handler()
        self._task_manager: "TaskManager | None" = self._init_task_manager()

    @abstractmethod
    def invoke(self, inputs: Dict, context: Context) -> Dict:
        """
        同步调用，一次性返回最终结果
        """
        pass

    @abstractmethod
    def stream(self, inputs: Dict, context: Context) -> Iterator[Any]:
        """
        流式调用，逐个 yield 中间结果
        """
        pass

    def register_workflows(self, workflows: List[Workflow]):
        self._controller_context_manager.workflow_mgr.add_workflows(workflows)

    def register_tools(self, tools):
        pass

    def _init_controller(self) -> "Controller | None":
        """
        留给子类按需实例化 Controller；默认返回 None
        """
        return None

    def _init_agent_handler(self) -> "AgentHandler | None":
        """
        留给子类按需实例化 AgentHandler；默认返回 None
        """
        return None

    def _init_task_manager(self) -> "TaskManager | None":
        """
        留给子类按需实例化 TaskManager；默认返回 None
        """
        return None

    def _init_controller_context_manager(self) -> Optional["ControllerContextMgr"]:
        """
        子类返回具体的 ControllerContextMgr 实例即可。
        默认返回 None，表示无需上下文管理。
        """
        return None
