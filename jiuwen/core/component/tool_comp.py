#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved

from dataclasses import dataclass, field
from typing import Dict, Any, AsyncIterator, Iterator, List

from jiuwen.core.common.exception.exception import JiuWenBaseException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.component.base import ComponentConfig, WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output
from jiuwen.core.utils.tool.base import Tool


@dataclass
class ToolComponentConfig(ComponentConfig):
    header: Dict[str, Any] = field(default_factory=dict)
    method: str = ''
    auth: Dict[str, Any] = field(default_factory=dict)
    pluginDependency: Dict[str, Any] = field(default_factory=dict)
    systemFields: Dict[str, Any] = field(default_factory=dict)
    exceptionEnable: bool = False
    description: str = ''
    url: str = ''
    streaming: bool = False
    userFields: Dict[str, Any] = field(default_factory=dict)
    response: List[Any] = field(default_factory=list)
    name: str = ''
    arguments: List[Any] = field(default_factory=list)
    id: str = ''

    needValidate: bool = True
    needConfirm: bool = False
    apiId: str = ''


class ToolExecutable(Executable):

    def __init__(self, config: ToolComponentConfig):
        super().__init__()
        self._config = config
        self._tool: Tool = None

    async def invoke(self, inputs: Input, context: Context) -> Output:
        if self._tool is None:
            self._tool = self.get_tool(context)
        validated = inputs.get('validate', False)
        user_field = inputs.get('userFields', None)
        if self._config.needValidate and not validated:
            self.validate_require_params(user_field)
        formatted_inputs = prepare_inputs(user_field, self.get_tool_param())
        try:
            response = self._tool.invoke(formatted_inputs)
            return self._create_output(response)
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.TOOL_COMPONENT_EXECUTE_ERROR.code,
                message='tool component execution error'
            ) from e

    async def stream(self, inputs: Input, context: Context) -> Iterator[Output]:
        pass

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        pass

    def _create_output(self, response):
        return response

    def get_tool(self, context: Context) -> Tool:
        pass

    def set_tool(self, tool: Tool):
        self._tool = tool
        return self

    def get_tool_param(self):
        return self._tool.params

    def validate_require_params(self, user_field):
        require_params = self.get_tool_param()
        params_dict = {param.name: param.descrpition for param in require_params}
        missing_params = {param for param in params_dict if param not in user_field}
        if missing_params:
            missing_params_dict = {param: params_dict[param] for param in missing_params}
            interrupt_message = {
                'type': 'MessageSubTypes.PLUGIN_PARAM_MISS.value',
                'tool_name': self._tool.name,
                'missing_params': missing_params_dict,
            }
            self.interrupt(interrupt_message)


TYPE_CASTER = {
    "str": str,
    "integer": int,
    "number": float,
    "bool": bool
}


def _transform_type(value, expected_type, key):
    expected_type = expected_type.lower()
    caster = TYPE_CASTER.get(expected_type)
    if caster:
        try:
            return caster(value)
        except(TypeError, ValueError) as e:
            raise JiuWenBaseException(
                error_code=StatusCode.TOOL_COMPONENT_PARAM_CHECK_ERROR.code,
                message=f'{StatusCode.TOOL_COMPONENT_PARAM_CHECK_ERROR.errmsg}'
                        f'param name is {key}, expected type: {expected_type}'
            ) from e
    return value


def prepare_inputs(user_field, defined_param) -> dict:
    define_dict = {}
    formatted_inputs = {}
    for param in defined_param:
        define_dict[param.name] = param
    for k, v in user_field.items():
        if define_dict.get(k):
            param = define_dict.get(k)
            expected_type = param.type
            formatted_inputs[k] = _transform_type(v, expected_type, k)
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.TOOL_COMPONENT_INPUTS_ERROR.code,
                message=f'{StatusCode.TOOL_COMPONENT_INPUTS_ERROR.errmsg}, param is {k}'
            )
    return formatted_inputs

class ToolComponent(WorkflowComponent):

    def __init__(self, config: ToolComponentConfig):
        super().__init__()
        self._config = config
        self._tool = None

    def to_executable(self) -> Executable:
        return ToolExecutable(self._config).set_tool(self._tool)

    def set_tool(self, tool: Tool):
        self._tool = tool
        return self
