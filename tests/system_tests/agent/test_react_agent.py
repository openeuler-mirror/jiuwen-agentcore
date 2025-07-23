import os
import unittest

from jiuwen.agent.common.schema import PluginSchema
from jiuwen.agent.react_agent import create_react_agent_config, create_react_agent, ReActAgent
from jiuwen.core.component.common.configs.model_config import ModelConfig
from jiuwen.core.utils.llm.base import BaseModelInfo
from jiuwen.core.utils.tool.service_api.param import Param
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi


API_BASE = os.getenv("API_BASE", "")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


class ReActAgentTest(unittest.IsolatedAsyncioTestCase):  # ① 关键改动
    DEFAULT_TEMPLATE = [
        dict(role="system", content="你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！")
    ]

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
    def _create_tool():
        weather_plugin = RestfulApi(
            name="WeatherReporter",
            description="天气查询插件",
            params=[
                Param(name="location", description="地点", type="string", required=True),
            ],
            path="http://127.0.0.1:9000/weather",
            headers={},
            method="GET",
            response=[],
        )
        return weather_plugin

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
                    }
                }
            }
        )
        return tool_info

    async def test_react_agent_invoke_with_real_plugin(self):
        tools_schema = [self._create_tool_schema()]
        model_config = self._create_model()
        prompt_template = self.DEFAULT_TEMPLATE

        react_agent_config = create_react_agent_config(
            agent_id="react_agent_123",
            agent_version="0.0.1",
            description="AI助手",
            plugins=tools_schema,
            workflows=[],
            model=model_config,
            prompt_template=prompt_template
        )

        react_agent: ReActAgent = create_react_agent(
            agent_config=react_agent_config,
            workflows=[],
            tools=[self._create_tool()]
        )

        result = await react_agent.invoke({"query": "查询杭州的天气"})
        print(f"ReActAgent 最终输出结果：{result}")
