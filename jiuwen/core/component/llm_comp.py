#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import json
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional, Iterator, AsyncIterator

from jiuwen.core.common.configs.model_config import ModelConfig
from jiuwen.core.common.constants.constant import USER_FIELDS
from jiuwen.core.common.enum.enum import WorkflowLLMResponseType, MessageRole
from jiuwen.core.common.exception.exception import JiuWenBaseException, InterruptException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.common.utils.utils import WorkflowLLMUtils, OutputFormatter
from jiuwen.core.component.base import ComponentConfig, WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.utils.llm.base import BaseChatModel
from jiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
from jiuwen.core.utils.prompt.template.template import Template
from jiuwen.core.utils.prompt.template.template_manager import TemplateManager

WORKFLOW_CHAT_HISTORY = "workflow_chat_history"
CHAT_HISTORY_MAX_TURN = 3
_ROLE = "role"
_CONTENT = "content"
ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统"}
_SPAN = "span"
_WORKFLOW_DATA = "workflow_data"
_ID = "id"
_TYPE = "type"
_INSTRUCTION_NAME = "instruction_name"
_TEMPLATE_NAME = "template_name"

RESPONSE_FORMAT_TO_PROMPT_MAP = {
    WorkflowLLMResponseType.JSON.value: {
        _INSTRUCTION_NAME: "jsonInstruction",
        _TEMPLATE_NAME: "llm_json_formatting"
    },
    WorkflowLLMResponseType.MARKDOWN.value: {
        _INSTRUCTION_NAME: "markdownInstruction",
        _TEMPLATE_NAME: "llm_markdown_formatting"
    }
}


@dataclass
class LLMCompConfig(ComponentConfig):
    model: 'ModelConfig' = None
    deployMode: str = ""
    template_content: List[Any] = field(default_factory=list)
    response_format: Dict[str, Any] = field(default_factory=dict)
    enable_history: bool = True
    user_fields: Dict[str, Any] = field(default_factory=dict)
    output_config: Dict[str, Any] = field(default_factory=dict)


class LLMExecutable(Executable):
    def __init__(self, component_config: LLMCompConfig):
        super().__init__()
        self._config = component_config
        self._llm: BaseChatModel = None
        self._initialized: bool = False
        self._context = None

    async def invoke(self, inputs: Input, context: Context) -> Output:
        try:
            self._set_context(context)
            model_inputs = self._prepare_model_inputs(inputs)
            response = await self._llm.ainvoke(model_inputs)
            return self._create_output(response)
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                                      message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(msg=str(e))) from e

    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        try:
            self._set_context(context)
            response_format_type = self._get_response_format().get(_TYPE)

            if response_format_type == WorkflowLLMResponseType.JSON.value:
                async for out in self._invoke_for_json_format(inputs):
                    yield out
            else:
                async for out in self._stream_with_chunks(inputs):
                    yield out
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.errmsg.format(msg=str(e))
            ) from e

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        raise InterruptException(
            error_code=StatusCode.CONTROLLER_INTERRUPTED_ERROR.code,
            message=json.dumps(message, ensure_ascii=False)
        )

    def _initialize_if_needed(self):
        if not self._initialized:
            try:
                self._llm = self._create_llm_instance()
                self._initialized = True
            except Exception as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                    message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(msg=str(e))
                ) from e

    def _create_llm_instance(self):
        return ModelFactory().get_model(self._config.model.model_provider, self._config.model.model_info)

    def _validate_inputs(self, inputs: Input) -> None:
        pass

    def _process_inputs(self, inputs: dict) -> dict:
        processed_inputs = {}
        if inputs:
            processed_inputs = inputs.copy()
            if self._context:
                chat_history: list = self._context.state.get(WORKFLOW_CHAT_HISTORY)
                chat_history = chat_history[:-1] if chat_history else []
                full_input = ""
                for history in chat_history[-CHAT_HISTORY_MAX_TURN:]:
                    full_input += "{}：{}\n".format(ROLE_MAP.get(history.get("role", "user"), "用户"),
                                                   history.get("content"))
                inputs.update({"CHAT_HISTORY": full_input})
        return processed_inputs

    def _build_prompt_message(self, inputs: dict) -> Template:
        template_content_list = self._config.template_content
        user_prompt = [element for element in template_content_list if element.get(_ROLE, "") == MessageRole.USER.value]
        if not user_prompt or not isinstance(user_prompt[0], dict):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(msg="Failed to retrieve llm template content")
            )
        default_template = Template(name="default", content=str(user_prompt[0].get("content")))
        return default_template.format(inputs)

    def _get_model_input(self, inputs: dict):
        return self._build_prompt_message(inputs)

    def _get_response_format(self):
        try:
            response_format = self._config.response_format
            if not response_format:
                return {}

            format_type = response_format.get(_TYPE)
            if not format_type or format_type not in RESPONSE_FORMAT_TO_PROMPT_MAP:
                return response_format

            format_config = RESPONSE_FORMAT_TO_PROMPT_MAP[format_type]
            instruction_name = format_config.get(_INSTRUCTION_NAME)

            if response_format.get(instruction_name):
                return response_format

            instruction_content = self._get_instruction_from_template(format_config)
            if instruction_content:
                response_format[instruction_name] = instruction_content

            return response_format

        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.errmsg
            ) from e

    def _get_instruction_from_template(self, format_config: dict) -> Optional[str]:
        template_name = format_config.get(_TEMPLATE_NAME)
        try:
            if not template_name:
                return None
            filters = self._build_template_filters()

            template_manager = TemplateManager()
            template = template_manager.get(name=template_name, filters=filters)

            return getattr(template, "content", None) if template else None
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.errmsg
            )(e)

    def _build_template_filters(self) -> dict:
        filters = {}

        model_name = self._config.model.model_info.model_name
        if model_name:
            filters["model_name"] = model_name

        return filters

    def _create_output(self, llm_output) -> Output:
        formatted_res = OutputFormatter.format_response(llm_output,
                                                        self._config.response_format,
                                                        self._config.output_config)
        return {USER_FIELDS: formatted_res}

    def _set_context(self, context):
        self._context = context

    def _prepare_model_inputs(self, inputs):
        self._initialize_if_needed()
        self._validate_inputs(inputs)

        user_inputs = inputs.get(USER_FIELDS)
        processed_inputs = self._process_inputs(user_inputs)
        return self._get_model_input(processed_inputs)

    async def _invoke_for_json_format(self, inputs: Input) -> AsyncIterator[Output]:
        model_inputs = self._prepare_model_inputs(inputs)
        llm_output = await self._llm.ainvoke(model_inputs)  # 如果 invoke 是异步接口，要加 await
        yield self._create_output(llm_output)

    async def _stream_with_chunks(self, inputs: Input) -> AsyncIterator[Output]:
        model_inputs = self._prepare_model_inputs(inputs)
        # 假设 self._llm.stream 本身就是异步生成器
        async for chunk in self._llm.astream(model_inputs):
            content = WorkflowLLMUtils.extract_content(chunk)
            yield content

    def _format_response_content(self, response_content: str) -> dict:
        pass


class LLMComponent(WorkflowComponent):
    def __init__(self, component_config: Optional[LLMCompConfig] = None):
        super().__init__()
        self._executable = None
        self._config = component_config

    @property
    def executable(self) -> LLMExecutable:
        if self._executable is None:
            self._executable = self.to_executable()
        return self._executable

    def to_executable(self) -> LLMExecutable:
        return LLMExecutable(self._config)
