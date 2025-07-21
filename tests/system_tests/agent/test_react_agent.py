import os
import unittest
from unittest.mock import patch

from jiuwen.agent.common.schema import WorkflowSchema, PluginSchema
from jiuwen.agent.react_agent import create_react_agent_config, create_react_agent
from jiuwen.core.component.common.configs.model_config import ModelConfig
from jiuwen.core.component.llm_comp import LLMCompConfig, LLMComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context, ExecutableContext
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.utils.llm.base import BaseModelInfo
from jiuwen.core.utils.tool.service_api.param import Param
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from jiuwen.core.workflow.base import Workflow
from jiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
from jiuwen.graph.pregel.graph import PregelGraph
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode

API_BASE = os.getenv("API_BASE", "")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")

USER_PROMPT_FOR_TRIP_PLANNING = "帮我生成一份{{location}}的旅行攻略，同时旅行时间为{{duration}}。注意：若未明确指定旅行时间，则默认为一天！"


class ReActAgentTest(unittest.TestCase):
    DEFAULT_TEMPLATE = [
        dict(role="system", content="你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！")
    ]

    @patch("jiuwen.core.utils.tool.service_api.restful_api.RestfulApi.invoke")
    def test_react_agent_invoke(self, mock_restfulapi_invoke):
        mock_restfulapi_invoke.return_value = {"result": "杭州今天天气晴，温度35度；注意局部地区有雷阵雨"}

        workflows_schema = [self._create_workflow_schema()]
        tools_schema = [self._create_tool_schema()]
        model_config = self._create_model()
        prompt_template = self.DEFAULT_TEMPLATE
        react_agent_config = create_react_agent_config(agent_id="react_agent_123", agent_version="0.0.1",
                                                       description="AI助手", plugins=tools_schema, workflows=[],
                                                       model=model_config, prompt_template=prompt_template)

        workflow = self._create_workflow()
        tool = self._create_tool()
        react_agent = create_react_agent(agent_config=react_agent_config,
                                         workflows=[],
                                         tools=[tool])

        context = Context(config=Config(), state=InMemoryState(), store=None)
        executable_context = ExecutableContext(context=context, node_id="react_agent")
        # inputs = dict(query="生成杭州一日游")
        inputs = dict(query="查询杭州今天的天气")
        result = react_agent.invoke(inputs, executable_context)
        print(result)

    @staticmethod
    def _create_model():
        return ModelConfig(model_provider=MODEL_PROVIDER,
                           model_info=BaseModelInfo(
                               model=MODEL_NAME,
                               api_base=API_BASE,
                               api_key=API_KEY,
                               temperature=0.7,
                               top_p=0.9,
                               timeout=30  # 添加超时设置
                           ))

    @staticmethod
    def _create_workflow_schema():
        workflow_inputs = {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "旅行的目的地",
                    "required": True
                },
                "duration": {
                    "type": "string",
                    "description": "旅行时长",
                    "required": False
                }
            }
        }
        return WorkflowSchema(id="workflow_123", name="TripPlanning", description="旅行攻略查询工作流",
                              version="1.0.0", inputs=workflow_inputs)

    @staticmethod
    def _create_workflow():
        workflow = Workflow(
            workflow_config=WorkflowConfig(
                metadata=WorkflowMetadata(id="workflow_123", name="TripPlanning", version="1.0.0")),
            graph=PregelGraph())
        start_component = MockStartNode("start")
        llm_component = ReActAgentTest._create_llm_component()
        end_component = MockEndNode("end")
        workflow.set_start_comp("start", start_component,
                            inputs_schema={
                                "location": "${userFields.location}",
                                "duration": "${userFields.duration}"
                            })

        workflow.add_workflow_comp("llm", llm_component,
                               inputs_schema={
                                   "userFields": {
                                       "location": "${start.location}",
                                       "duration": "{start.duration}"
                                   }
                               })
        workflow.set_end_comp("end", end_component,
                          inputs_schema={
                              "output": "${llm.userFields}"
                          })
        workflow.add_connection("start", "llm")
        workflow.add_connection("llm", "end")
        return workflow

    @staticmethod
    def _create_llm_component():
        model_config = ModelConfig(model_provider=MODEL_PROVIDER,
                           model_info=BaseModelInfo(
                               model=MODEL_NAME,
                               api_base=API_BASE,
                               api_key=API_KEY,
                               temperature=0.7,
                               top_p=0.9,
                               timeout=30  # 添加超时设置
                           ))
        config = LLMCompConfig(
            model=model_config,
            template_content=[{"role": "user", "content": USER_PROMPT_FOR_TRIP_PLANNING}],
            response_format={"type": "text"},
            output_config={"result": {"type": "string", "required": True}},
        )
        return LLMComponent(config)

    @staticmethod
    def _create_tool():
        mock_plugin = RestfulApi(
            name="WeatherReporter",
            description="天气查询插件",
            params=[
                Param(name="location", description="地点", type="string", required=True),
                Param(name="date", description="日期", type="string", required=True),
            ],
            path="http://127.0.0.1:8000",
            headers={},
            method="GET",
            response=[],
        )
        return mock_plugin

    @staticmethod
    def _create_tool_schema():
        tool_info = PluginSchema(
            name='WeatherReporter',
            description='天气查询插件',
            inputs={
                "type": "object",
                "properties": {
                        "location": {
                            "type": "string",
                            "description": "天气查询的地点",
                            "required": True
                        },
                        "date": {
                            "type": "string",
                            "description": "天气查询的日期",
                            "required": True
                        }
                    }
            }
        )
        return tool_info
