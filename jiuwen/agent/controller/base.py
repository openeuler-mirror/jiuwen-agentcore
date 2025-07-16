#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""Controller of Agent"""
from pydantic import BaseModel

from jiuwen.agent.config.base import AgentConfig


class ControllerOutput(BaseModel):
    ...


class ControllerInput(BaseModel):
    ...


class Controller:
    def __init__(self, config: AgentConfig, context_mgr):
        self._config = config
        self._agent_handler = None
        self._context_mgr = context_mgr

    def invoke(self, inputs: ControllerInput) -> ControllerOutput:
        pass
