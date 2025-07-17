import pytest
from unittest.mock import Mock, patch

from jiuwen.agent.config.workflow_config import WorkflowAgentConfig
from jiuwen.agent.workflow_agent import WorkflowAgent


class TestWorkflowAgent:
    # 在所有测试方法前一次性打补丁
    @pytest.fixture(autouse=True, scope="class")
    def _patch_deps(self):
        # 把私有工厂方法替换掉
        with patch.object(
                WorkflowAgent, "_init_agent_handler", autospec=True
        ) as mock_handler, patch.object(
            WorkflowAgent, "_init_controller_context_manager", autospec=True
        ):
            # 返回统一的 mock handler
            handler = Mock()
            handler.invoke = Mock(side_effect=lambda st: {"mock": st.func_name})
            mock_handler.return_value = handler
            yield

    # 真正实例化
    @pytest.fixture(scope="class")
    def agent(self):
        return WorkflowAgent(WorkflowAgentConfig())

    # ---------- 测试用例 ----------
    def test_invoke_single(self, agent):
        inputs = {"workflows": [{"name": "echo", "params": {"text": "hi"}}]}
        result = agent.invoke(inputs)
        assert result == {"outputs": []}
