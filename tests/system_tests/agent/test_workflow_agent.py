# tests/test_workflow_agent_invoke_real.py
import os
import unittest

import pytest
from unittest.mock import patch

from jiuwen.agent.common.schema import WorkflowSchema
from jiuwen.agent.config.workflow_config import WorkflowAgentConfig
from jiuwen.core.component.branch_comp import BranchComponent
from jiuwen.core.component.common.configs.model_config import ModelConfig
from jiuwen.core.component.intent_detection_comp import IntentDetectionComponent, IntentDetectionConfig
from jiuwen.core.component.llm_comp import LLMComponent, LLMCompConfig
from jiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
from jiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
from jiuwen.core.context.agent_context import AgentContext
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context, ExecutableContext
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.utils.llm.base import BaseModelInfo
from jiuwen.core.utils.prompt.template.template import Template
from jiuwen.core.utils.tool.service_api.param import Param
from jiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from jiuwen.core.workflow.base import Workflow
from jiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
from jiuwen.graph.pregel.graph import PregelGraph
from tests.system_tests.workflow.test_real_workflow import RealWorkflowTest, MODEL_PROVIDER, MODEL_NAME, API_BASE, \
    API_KEY, _FINAL_RESULT, _QUESTIONER_USER_TEMPLATE, _QUESTIONER_SYSTEM_TEMPLATE
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode

API_BASE = os.getenv("API_BASE", "")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
# Mock RESTful Api 元信息
_MOCK_TOOL = RestfulApi(
    name="test",
    description="test",
    params=[
        Param(name="location", description="地点", type="string"),
        Param(name="date", description="日期", type="int"),
    ],
    path="http://127.0.0.1:8000",
    headers={},
    method="GET",
    response=[],
)


class WorkflowAgentTest(unittest.IsolatedAsyncioTestCase):
    """专门用于测试 WorkflowAgent.invoke 的类。"""

    @staticmethod
    def _create_model_config() -> ModelConfig:
        """根据环境变量构造模型配置。"""
        return ModelConfig(
            model_provider=MODEL_PROVIDER,
            model_info=BaseModelInfo(
                model=MODEL_NAME,
                api_base=API_BASE,
                api_key=API_KEY,
                temperature=0.7,
                top_p=0.9,
                timeout=30,
            ),
        )

    @staticmethod
    def _create_intent_detection_component() -> IntentDetectionComponent:
        """创建意图识别组件。"""
        model_config = RealWorkflowTest._create_model_config()
        user_prompt = """
        {{user_prompt}}

        当前可供选择的功能分类如下：
        {{category_info}}

        用户与助手的对话历史：
        {{chat_history}}

        当前输入：
        {{input}}

        请根据当前输入和对话历史分析并输出最适合的功能分类。输出格式为 JSON：
        {"class": "分类xx"}
        如果没有合适的分类，请输出 {{default_class}}。
        """
        config = IntentDetectionConfig(
            user_prompt="请判断用户意图",
            category_info="",
            category_list=["分类1", "分类2"],
            category_name_list=["旅游", "天气"],
            default_class="分类1",
            model=model_config,
            intent_detection_template=Template(
                name="default",
                content=[{"role": "user", "content": user_prompt}],
            ),
            enable_input=True,
        )
        return IntentDetectionComponent(config)

    @staticmethod
    def _create_llm_component() -> LLMComponent:
        """创建 LLM 组件，仅用于抽取结构化字段（location/date）。"""
        model_config = RealWorkflowTest._create_model_config()
        config = LLMCompConfig(
            model=model_config,
            template_content=[{"role": "user", "content": "{{query}}"}],
            response_format={"type": "json"},
            output_config={
                "location": {"type": "string", "description": "地点", "required": True}
            },
        )
        return LLMComponent(config)

    @staticmethod
    def _create_questioner_component() -> QuestionerComponent:
        """创建信息收集组件。"""
        key_fields = [
            FieldInfo(field_name="location", description="地点", required=True),
            FieldInfo(
                field_name="date",
                description="时间",
                required=True,
                default_value="today",
            ),
        ]
        model_config = RealWorkflowTest._create_model_config()
        config = QuestionerConfig(
            model=model_config,
            question_content="",
            extract_fields_from_response=True,
            field_names=key_fields,
            with_chat_history=False,
            prompt_template=[
                {"role": "system", "content": _QUESTIONER_SYSTEM_TEMPLATE},
                {"role": "user", "content": _QUESTIONER_USER_TEMPLATE},
            ],
        )
        return QuestionerComponent(config)

    @staticmethod
    def _create_plugin_component() -> ToolComponent:
        """创建插件组件，真正调用外部 RESTful API。"""
        tool_config = ToolComponentConfig(needValidate=False)
        return ToolComponent(tool_config)

    def _build_workflow(
            self,
            mock_plugin_get_tool,
            mock_plugin_invoke,
    ) -> tuple[Context, Workflow]:
        """
        根据 mock 工具函数构建完整工作流拓扑。

        返回 (context, workflow) 二元组，可直接用于 invoke。
        """
        # 1. Mock 插件行为
        mock_plugin_get_tool.return_value = _MOCK_TOOL
        mock_plugin_invoke.return_value = {"result": _FINAL_RESULT}

        # 2. 初始化工作流与上下文
        id = "test_weather_agent"
        version = "1.0"
        name = "weather"
        workflow_config = WorkflowConfig(
            metadata=WorkflowMetadata(
                name=name,
                id=id,
                version=version,
            )
        )
        flow = Workflow(
            workflow_config=workflow_config,
            graph=PregelGraph(),
        )
        context = Context(config=Config(), state=InMemoryState(), store=None)
        # 3. 实例化各组件
        start = MockStartNode("start")
        intent = self._create_intent_detection_component()
        llm = self._create_llm_component()
        questioner = self._create_questioner_component()
        plugin = self._create_plugin_component()
        end = MockEndNode("end")
        branch = BranchComponent()

        # 4. 注册组件到工作流
        flow.set_start_comp(
            "start",
            start,
            inputs_schema={"query": "${query}"},
        )
        flow.add_workflow_comp(
            "intent",
            intent,
            inputs_schema={"input": "${query}"},
        )
        flow.add_workflow_comp(
            "llm",
            llm,
            inputs_schema={"userFields": {"query": "${start.query}"}},
        )
        flow.add_workflow_comp(
            "questioner",
            questioner,
            inputs_schema={"query": "${start.query}"},  # TODO：临时 mock
        )
        flow.add_workflow_comp(
            "plugin",
            plugin,
            inputs_schema={
                "userFields": "${questioner.userFields.key_fields}",
                "validated": True,
            },
        )
        flow.set_end_comp("end", end, inputs_schema={"output": "${plugin.result}"})

        # 5. 分支逻辑
        flow.add_workflow_comp("branch", branch, inputs_schema={
            "res": "${intent.classificationId}"
        })
        branch.add_branch("${intent.classificationId} == 1", ["llm"], "1")
        branch.add_branch("${intent.classificationId} > 1", ["end"], "2")

        # 6. 连接拓扑
        flow.add_connection("start", "intent")
        flow.add_connection("intent", "branch")
        flow.add_connection("llm", "questioner")
        flow.add_connection("questioner", "plugin")
        flow.add_connection("plugin", "end")

        return context, flow

    @staticmethod
    def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
        return WorkflowSchema(id=id,
                              name=name,
                              description="天气查询工作流",
                              version=version,
                              inputs={"query": {
                                  "type": "string",
                              }})

    def _create_agent(self, workflow):
        """根据 workflow 实例化 WorkflowAgent。"""
        from jiuwen.agent.workflow_agent import WorkflowAgent  # 你给出的类
        workflow_id = workflow.config().metadata.id
        workflow_name = workflow.config().metadata.name
        workflow_version = workflow.config().metadata.version
        schema = self._create_workflow_schema(workflow_id, workflow_name, workflow_version)
        config = WorkflowAgentConfig(
            id="test_weather_agent",
            version="0.1.0",
            description="测试用天气 agent",
            workflows=[schema],
        )
        agent = WorkflowAgent(config, agent_context=AgentContext())
        agent.bind_workflows([workflow])
        return agent

    # ===== 核心测试用例 =====
    @pytest.mark.asyncio
    async def test_real_workflow_agent_invoke(self):
        """端到端测试：WorkflowAgent.invoke 走完整链路（插件被 mock）。"""
        with (
            patch("jiuwen.core.component.tool_comp.ToolExecutable.get_tool") as mock_get_tool,
            patch("jiuwen.core.utils.tool.service_api.restful_api.RestfulApi.invoke") as mock_invoke,
        ):
            # 2. 固定插件返回
            mock_get_tool.return_value = _MOCK_TOOL
            mock_invoke.return_value = {"result": "上海今天晴 30°C"}

            # 3. 构造真实 workflow
            _, workflow = self._build_workflow(
                mock_plugin_get_tool=mock_get_tool,
                mock_plugin_invoke=mock_invoke,

            )

            # 4. 构造 agent 并调用
            agent = self._create_agent(workflow)
            result = await agent.invoke({"query": "查询上海的天气", "conversation_id": "c123"})

            # 5. 断言
            assert result == {'output': '上海今天晴 30°C'}
