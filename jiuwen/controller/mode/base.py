#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""Controller of Agent"""
from jiuwen.controller.config.base import AgentConfig
from jiuwen.core.context.context import Context
from jiuwen.core.graph.executable import Input, Output


class Controller:
    def __init__(self, config: AgentConfig):
        self._config = config
        self._agent_sdk = None

    def invoke(self, inputs: Input, context: Context) -> Output:
        pass
