import asyncio
import unittest
from unittest.mock import patch

from pydantic import BaseModel

from jiuwen.core.common.configs.model_config import ModelConfig
from jiuwen.core.component.base import StartComponent, EndComponent
# from jiuwen.core.component.llm_comp import LLMComponent, LLMCompConfig
from jiuwen.core.component.questioner_comp import QuestionerInteractState, FieldInfo, QuestionerConfig, \
    QuestionerComponent
from jiuwen.core.context.config import Config
from jiuwen.core.context.context import Context
from jiuwen.core.context.memory.base import InMemoryState
from jiuwen.core.context.store import MemoryStore
from jiuwen.core.utils.prompt.template.template import Template
from jiuwen.core.workflow.base import Workflow, WorkflowConfig
from jiuwen.graph.pregel.graph import PregelGraph
from tests.unit_tests.workflow.test_mock_node import MockStartNode, MockEndNode
from tests.unit_tests.workflow.test_workflow import create_flow


class MockLLMModel:
    pass

class QuestionerTest(unittest.TestCase):
    def invoke_workflow(self, inputs: dict, context: Context, flow: Workflow):
        loop = asyncio.get_event_loop()
        feature = asyncio.ensure_future(flow.invoke(inputs=inputs, context=context))
        loop.run_until_complete(feature)
        return feature.result()

    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._invoke_llm_for_extraction")
    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._build_llm_inputs")
    @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._init_prompt")
    @patch("jiuwen.core.utils.llm.model_utils.model_factory.ModelFactory.get_model")
    def test_questioner_component_in_workflow_initial_ask(self, mock_get_model, mock_init_prompt, mock_llm_inputs,
                                                          mock_extraction):
        mock_get_model.return_value = MockLLMModel()
        mock_prompt_template = [
            dict(role="system", content="系统提示词"),
            dict(role="user", content="你是一个AI助手")
        ]
        mock_init_prompt.return_value = Template(name="test", content=mock_prompt_template)
        mock_llm_inputs.return_value = mock_prompt_template
        mock_extraction.return_value = dict(location="hangzhou")

        context = Context(config=Config(), state=InMemoryState(), store=None, tracer=None)
        flow = create_flow()

        key_fields = [
            FieldInfo(field_name="location", description="地点", required=True),
            FieldInfo(field_name="time", description="时间", required=True, default_value="today")
        ]

        start_component = MockStartNode("s")
        end_component = MockEndNode("e")

        model_config = ModelConfig(model_provider="openai")
        questioner_config = QuestionerConfig(
            model=model_config,
            question_content="",
            extract_fields_from_response=True,
            field_names=key_fields,
            with_chat_history=False
        )
        questioner_component = QuestionerComponent(questioner_comp_config=questioner_config)

        flow.set_start_comp("s", start_component)
        flow.set_end_comp("e", end_component)
        flow.add_workflow_comp("questioner", questioner_component)

        flow.add_connection("s", "questioner")
        flow.add_connection("questioner", "e")

        result = self.invoke_workflow({}, context, flow)
        print(result)


    @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._load_state_from_context")
    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._invoke_llm_for_extraction")
    @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._build_llm_inputs")
    @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._init_prompt")
    @patch("jiuwen.core.utils.llm.model_utils.model_factory.ModelFactory.get_model")
    def test_questioner_component_in_workflow_repeat_ask(self, mock_get_model, mock_init_prompt, mock_llm_inputs,
                                                         mock_extraction, mock_state_from_context):
        mock_get_model.return_value = MockLLMModel()
        mock_prompt_template = [
            dict(role="system", content="系统提示词"),
            dict(role="user", content="你是一个AI助手")
        ]
        mock_init_prompt.return_value = Template(name="test", content=mock_prompt_template)
        mock_llm_inputs.return_value = mock_prompt_template
        mock_extraction.return_value = dict(time="tomorrow")
        state = QuestionerInteractState(extracted_key_fields=dict(location="hangzhou"))
        mock_state_from_context.return_value = state

        context = Context(config=Config(), state=InMemoryState(), store=None, tracer=None)
        flow = create_flow()

        key_fields = [
            FieldInfo(field_name="location", description="地点", required=True),
            FieldInfo(field_name="time", description="时间", required=True, default_value="today")
        ]

        start_component = MockStartNode("s")
        end_component = MockEndNode("e")

        model_config = ModelConfig(model_provider="openai")
        questioner_config = QuestionerConfig(
            model=model_config,
            question_content="",
            extract_fields_from_response=True,
            field_names=key_fields,
            with_chat_history=False
        )
        questioner_component = QuestionerComponent(questioner_comp_config=questioner_config)

        flow.set_start_comp("s", start_component)
        flow.set_end_comp("e", end_component)
        flow.add_workflow_comp("questioner", questioner_component)

        flow.add_connection("s", "questioner")
        flow.add_connection("questioner", "e")

        result = self.invoke_workflow({}, context, flow)
        print(result)


    # @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._load_state_from_context")
    # @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._invoke_llm_for_extraction")
    # @patch("jiuwen.core.component.questioner_comp.QuestionerDirectReplyHandler._build_llm_inputs")
    # @patch("jiuwen.core.component.questioner_comp.QuestionerExecutable._init_prompt")
    # @patch("jiuwen.core.utils.llm.model_utils.model_factory.ModelFactory.get_model")
    # def test_workflow_with_llm_questioner_tool(mock_get_model, mock_init_prompt, mock_llm_inputs, mock_extraction,
    #                                            mock_state_from_context):
    #     mock_get_model.return_value = MockLLMModel()
    #     mock_prompt_template = [
    #         dict(role="system", content="系统提示词"),
    #         dict(role="user", content="你是一个AI助手")
    #     ]
    #     mock_init_prompt.return_value = Template(name="test", content=mock_prompt_template)
    #     mock_llm_inputs.return_value = mock_prompt_template
    #     mock_extraction.return_value = dict(time="tomorrow")
    #     state = QuestionerInteractState(extracted_key_fields=dict(location="hangzhou"))
    #     mock_state_from_context.return_value = state
    #
    #     context = Context(Config(), InMemoryState(), MemoryStore())
    #     flow = Workflow(WorkflowConfig())
    #     model_config = ModelConfig(model_provider="openai")
    #
    #     key_fields = [
    #         FieldInfo(field_name="location", description="地点", required=True),
    #         FieldInfo(field_name="time", description="时间", required=True, default_value="today")
    #     ]
    #
    #     start_component = StartComponent()
    #     end_component = EndComponent()
    #
    #     llm_config = LLMCompConfig()
    #     llm_component = LLMComponent(llm_config)
    #
    #     questioner_config = QuestionerConfig(
    #         model=model_config,
    #         question_content="",
    #         extract_fields_from_response=True,
    #         field_names=key_fields,
    #         with_chat_history=False
    #     )
    #
    #     questioner_component = QuestionerComponent(questioner_comp_config=questioner_config)
    #
    #     flow.set_start_comp("s", start_component)
    #     flow.set_end_comp("e", end_component)
    #     flow.add_workflow_comp("questioner", questioner_component)
    #     flow.add_workflow_comp("llm", llm_component)
    #
    #     flow.add_connection("s", "llm")
    #     flow.add_connection("llm", "questioner")
    #     flow.add_connection("questioner", "e")
    #
    #     flow.invoke({"mock_key": "mock_value"}, context)
