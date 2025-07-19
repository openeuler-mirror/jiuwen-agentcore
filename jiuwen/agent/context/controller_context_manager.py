from jiuwen.agent.config.base import AgentConfig
from jiuwen.agent.context.message_manager import MessageMgr
from jiuwen.agent.context.model_manager import ModelMgr
from jiuwen.agent.context.tool_manager import ToolMgr
from jiuwen.agent.context.workflow_manager import WorkflowMgr

class ControllerContextMgr:
    """
    Agent上下文管理器：
    """

    def __init__(self, agent_config: AgentConfig):
        self.workflow_mgr = WorkflowMgr()
        self.tool_mgr = ToolMgr()
        self.model_mgr = ModelMgr()
        self.message_mgr = MessageMgr()
