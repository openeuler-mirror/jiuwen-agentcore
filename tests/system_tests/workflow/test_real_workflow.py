import asyncio
import unittest
from unittest.mock import patch

from jiuwen.core.common.configs.model_config import ModelConfig
from jiuwen.core.component.llm_comp import LLMCompConfig, LLMComponent, WORKFLOW_CHAT_HISTORY
from jiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
from jiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
from jiuwen.core.context.config import WorkflowConfig, Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.utils.llm.base import BaseModelInfo
from jiuwen.core.utils.prompt.template.template import Template
from jiuwen.core.utils.tool.service_api.param import Param
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from jiuwen.core.workflow.base import Workflow
from jiuwen.graph.pregel.graph import PregelGraph
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode

MOCK_TOOL = RestfulApi(
    name="test",
    description="test",
    params=[Param(name="location", description="location", type='string'),
            Param(name="date", description="date", type='int')],
    path="http://127.0.0.1:8000",
    headers={},
    method="GET",
    response=[],
)
FINAL_RESULT = "Success"
API_BASE = ""
API_KEY = ""
MODEL_NAME = ""
MODEL_PROVIDER = ""


class RealWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def invoke_workflow(self, inputs: dict, context: Context, flow: Workflow):
        feature = asyncio.ensure_future(flow.invoke(inputs=inputs, context=context))
        self.loop.run_until_complete(feature)
        return feature.result()

    def _create_flow(self) -> Workflow:
        return Workflow(workflow_config=WorkflowConfig(), graph=PregelGraph())

    @patch('jiuwen.core.utils.tool.service_api.restful_api.RestfulApi.invoke')
    @patch('jiuwen.core.component.tool_comp.ToolExecutable.get_tool')
    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._invoke_llm_for_extraction")
    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._build_llm_inputs")
    @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._init_prompt")
    def test_workflow_llm_questioner_plugin(self, mock_questioner_init_prompt,
                                            mock_questioner_llm_inputs,
                                            mock_questioner_extraction, mock_plugin_get_tool, mock_plugin_invoke):
        """Start -> LLM -> Questioner -> Plugin -> End"""
        # LLM的mock逻辑
        # fake_llm = AsyncMock()
        # fake_llm.ainvoke = AsyncMock(return_value="mocked response")
        # mock_get_model.return_value = fake_llm

        # 提问器的mock逻辑
        mock_prompt_template = [
            dict(role="system", content="系统提示词"),
            dict(role="user", content="你是一个AI助手")
        ]
        mock_questioner_init_prompt.return_value = Template(name="test", content=mock_prompt_template)
        mock_questioner_llm_inputs.return_value = mock_prompt_template
        mock_questioner_extraction.return_value = dict(location="hangzhou")

        # 插件组件的mock逻辑
        mock_plugin_get_tool.return_value = MOCK_TOOL
        mock_plugin_invoke.return_value = {"result": FINAL_RESULT}

        # 实例化工作流和上下文
        flow = self._create_flow()
        context = Context(config=Config(), state=InMemoryState(), store=None)
        # context.state.update({WORKFLOW_CHAT_HISTORY: []})
        # 实例化组件
        start_component = MockStartNode("start")
        llm_component = self._create_llm_component()
        questioner_component = self._create_questioner_component()
        plugin_component = self._create_plugin_component()
        end_component = MockEndNode("end")

        # 向工作流添加组件
        flow.set_start_comp("start", start_component,
                            inputs_schema={
                                "query": "${query}"
                            })

        flow.add_workflow_comp("llm", llm_component,
                               inputs_schema={
                                   "userFields": {
                                       "query": "${start.query}"
                                   }
                               })
        flow.add_workflow_comp("questioner", questioner_component,
                               inputs_schema={
                                   "query": "${llm.userFields.result}"
                               })
        flow.add_workflow_comp("plugin", plugin_component,
                               inputs_schema={
                                   "userFields": "${questioner.userFields.key_fields}",
                                   'validated': True
                               })
        flow.set_end_comp("end", end_component,
                          inputs_schema={
                              "output": "${plugin.result}"
                          })

        # 组件间的连边
        flow.add_connection("start", "llm")
        flow.add_connection("llm", "questioner")
        flow.add_connection("questioner", "plugin")
        flow.add_connection("plugin", "end")

        # 执行工作流
        inputs = dict(query="查询杭州景点")
        result = self.invoke_workflow(inputs, context, flow)
        assert result == dict(output=FINAL_RESULT)

    @staticmethod
    def _create_llm_component():
        model_config = RealWorkflowTest._get_mode_config()
        config = LLMCompConfig(
            model=model_config,
            template_content=[{"role": "user", "content": "{{query}}"}],
            response_format={"type": "text"},
            output_config={"result": {"type": "string", "required": True}},
        )
        return LLMComponent(config)

    @staticmethod
    def _get_mode_config():
        model_config = ModelConfig(model_provider=MODEL_PROVIDER,
                                   model_info=BaseModelInfo(
                                       model_name=MODEL_NAME,
                                       api_base=API_BASE,
                                       api_key=API_KEY,
                                       temperature=0.7,
                                       top_p=0.9,
                                       timeout=30  # 添加超时设置
                                   ))
        return model_config

    @staticmethod
    def _create_questioner_component():
        key_fields = [
            FieldInfo(field_name="location", description="地点", required=True),
            FieldInfo(field_name="date", description="时间", required=True, default_value="today")
        ]
        model_config = RealWorkflowTest._get_mode_config()
        questioner_config = QuestionerConfig(
            model=model_config,
            question_content="",
            extract_fields_from_response=True,
            field_names=key_fields,
            with_chat_history=False
        )
        return QuestionerComponent(questioner_comp_config=questioner_config)

    @staticmethod
    def _create_plugin_component():
        tool_config = ToolComponentConfig(needValidate=False)
        return ToolComponent(tool_config)
