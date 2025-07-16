#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""Handler of Agent"""
from typing import Dict, Callable

from jiuwen.controller.common.enum import SubTaskType
from jiuwen.core.common.exception.exception import JiuWenBaseException


class AgentSdk:
    def __init__(self):
        self._function_map: Dict[SubTaskType, Callable[[dict], dict]] = {
            SubTaskType.WORKFLOW: self.invoke_workflow,
            SubTaskType.PLUGIN: self.invoke_plugin
        }

    def invoke(self, sub_task_type: SubTaskType, inputs: dict):
        handler = self._function_map.get(sub_task_type)
        if not handler:
            raise JiuWenBaseException()
        return handler(inputs)

    def invoke_workflow(self, inputs: dict):
        return dict()

    def invoke_plugin(self, inputs: dict):
        return dict()

    def invoke_llm(self, inputs: dict):
        return dict()

    def send_message(self, inputs: dict):
        return dict()


class AgentSdkImpl(AgentSdk):
    pass
