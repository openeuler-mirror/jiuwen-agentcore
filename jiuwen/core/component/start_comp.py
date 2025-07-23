#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from abc import ABC
from copy import deepcopy
from typing import List, Any, Dict, Optional, Iterator, AsyncIterator
import json


from jiuwen.core.common.constants.constant import USER_FIELDS, SYSTEM_FIELDS
from jiuwen.core.common.exception.exception import JiuWenBaseException, InterruptException
from jiuwen.core.common.exception.status_code import StatusCode
from jiuwen.core.component.base import WorkflowComponent
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Executable, Input, Output




class Start(Executable,WorkflowComponent):
    def __init__(self, node_id: str, conf: dict):
        super().__init__()
        self.conf = conf
        self.node_id  = node_id

    async def invoke(self, inputs: Input, context: Context) -> Output:
        self._validate_inputs(inputs)
        inputs_copy = self._fill_default_values(deepcopy(inputs))
        return dict(
            {
                SYSTEM_FIELDS: {
                    "query": inputs_copy.get("systemFields").get("query", ""),
                    "dialogueHistory": [],
                    "conversationHistory": inputs_copy.pop("conversationHistory", []),
                },
                USER_FIELDS: inputs_copy
            }
        )

    def _fill_default_values(self, inputs: Input):
        user_defined_variables = self.conf.get(USER_FIELDS, {}).get("inputs", [])
        default_maps = {var["id"]: var["default_value"]
                        for var in user_defined_variables
                        if "id" in var and "default_value" in var and var["default_value"] is not None}
        return default_maps | inputs

    def _validate_inputs(self, inputs: Input):
        user_defined_variables = self.conf.get(USER_FIELDS, {}).get("inputs", {})
        variables_not_given = []
        for variable in [var for var in user_defined_variables if var.get("required", False)]:
            variable_name = variable.get("id", "")
            if variable_name not in inputs:
                variables_not_given.append(variable_name)
            if variables_not_given:
                raise JiuWenBaseException(error_code=StatusCode.WORKFLOW_START_MISSING_GLOBAL_VARIABLE_VALUE.code,
                                          message=StatusCode.WORKFLOW_START_MISSING_GLOBAL_VARIABLE_VALUE.errmsg.format(
                                              variable_names=variables_not_given))


    async def stream(self, inputs: Input, context: Context) -> AsyncIterator[Output]:
        pass

    async def collect(self, inputs: AsyncIterator[Input], contex: Context) -> Output:
        pass

    async def transform(self, inputs: AsyncIterator[Input], context: Context) -> AsyncIterator[Output]:
        pass

    async def interrupt(self, message: dict):
        raise InterruptException(
            error_code=StatusCode.CONTROLLER_INTERRUPTED_ERROR.code,
            message=json.dumps(message, ensure_ascii=False)
        )

    def to_executable(self) -> Executable:
        return self