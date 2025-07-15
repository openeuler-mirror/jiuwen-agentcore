import asyncio
import sys
import types

import pytest
from unittest.mock import Mock

fake_base = types.ModuleType("base")
fake_base.logger = Mock()

fake_exception_module = types.ModuleType("base")
fake_exception_module.JiuWenBaseException = Mock()

sys.modules["jiuwen.core.common.logging.base"] = fake_base
sys.modules["jiuwen.core.common.exception.base"] = fake_exception_module

from jiuwen.core.workflow.base import Workflow
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode
from tests.unit_tests.workflow.test_workflow import create_flow, create_context

from unittest.mock import patch, AsyncMock

from jiuwen.core.common.configs.model_config import ModelConfig
from jiuwen.core.common.constants.constant import USER_FIELDS
from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.component.llm_comp import LLMCompConfig, LLMExecutable, LLMComponent
from jiuwen.core.context.context import Context
from jiuwen.core.utils.llm.base import BaseModelInfo


@pytest.fixture
def fake_ctx():
    from unittest.mock import MagicMock
    ctx = MagicMock(spec=Context)
    ctx.store = MagicMock()
    ctx.store.read.return_value = []
    return ctx


@pytest.fixture
def fake_input():
    return lambda **kw: {USER_FIELDS: kw}


@pytest.fixture
def fake_model_config() -> ModelConfig:
    """构造一个最小可用的 ModelConfig"""
    return ModelConfig(
        model_provider="openai",
        model_info=BaseModelInfo(
            api_key="sk-fake",
            api_base="https://api.openai.com/v1",
            model_name="gpt-3.5-turbo",
            temperature=0.8,
            top_p=0.9,
            streaming=False,
            timeout=30.0,
        ),
    )


@patch(
    "jiuwen.core.utils.llm.model_utils.model_factory.ModelFactory.get_model",
    autospec=True,
)
class TestLLMExecutableInvoke:

    @pytest.mark.asyncio
    async def test_invoke_success(
            self,
            mock_get_model,  # 这就是补丁
            fake_ctx,
            fake_input,
            fake_model_config,
    ):
        config = LLMCompConfig(
            model=fake_model_config,
            template_content=[{"role": "user", "content": "Hello {name}"}],
            response_format={"type": "text"},
            output_config={"result": {
                "type": "string",
                "required": True,
            }},
        )
        exe = LLMExecutable(config)

        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value="mocked response")
        mock_get_model.return_value = fake_llm

        output = await exe.invoke(fake_input(name="pytest"), fake_ctx)

        assert output[USER_FIELDS] == {'result': 'mocked response'}
        fake_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_llm_exception(
            self,
            mock_get_model,
            fake_ctx,
            fake_input,
            fake_model_config,
    ):
        config = LLMCompConfig(model=fake_model_config, template_content=[{"role": "user", "content": "Hello {name}"}])
        exe = LLMExecutable(config)

        fake_llm = Mock()
        fake_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))
        mock_get_model.return_value = fake_llm

        with pytest.raises(JiuWenBaseException) as exc_info:
            await exe.invoke(fake_input(), fake_ctx)

        assert "LLM down" in str(exc_info.value.message)

    @pytest.mark.asyncio  # 新增
    async def test_llm_in_workflow(
            self,
            mock_get_model,
            fake_model_config,
    ):
        """LLM 节点在完整工作流中的异步测试"""
        context = create_context()

        # 1. 打桩 LLM
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(return_value="mocked response")
        mock_get_model.return_value = fake_llm

        # 2. 构造工作流
        flow = create_flow()
        flow.set_start_comp("start", MockStartNode("start"))
        flow.set_end_comp(
            "end",
            MockEndNode("end"),
            inputs_schema={"a": "${a.result}", "b": "${b.result}"},
        )

        config = LLMCompConfig(
            model=fake_model_config,
            template_content=[{"role": "user", "content": "Hello {name}"}],
            response_format={"type": "text"},
            output_config={"result": {"type": "string", "required": True}},
        )
        llm_comp = LLMComponent(config)
        flow.add_workflow_comp("llm", llm_comp)

        flow.add_connection("start", "llm")
        flow.add_connection("llm", "end")

        # 3. 直接异步调用
        result = await flow.invoke(inputs={"a": 2}, context=context)
        assert result is not None
